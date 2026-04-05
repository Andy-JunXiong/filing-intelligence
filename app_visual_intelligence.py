from __future__ import annotations

import json
import csv
import io
from pathlib import Path

try:
    import plotly.graph_objects as go
except ImportError:  # pragma: no cover - dependency guard
    go = None

try:
    import streamlit as st
except ImportError:  # pragma: no cover - dependency guard
    st = None


VISUALIZATION_DIR = Path("data") / "visualizations"
DATASET_FILES = {
    "Profit Pool Map": "profit_pool_scatter.json",
    "Growth vs Profit": "growth_vs_profit.json",
    "Infrastructure Map": "capex_vs_scale.json",
}
ROLE_COLORS = {
    "Infrastructure Builder": "#1f77b4",
    "AI Hardware Platform": "#d62728",
    "AI Platform Scale": "#2ca02c",
    "Multi-Role": "#9467bd",
    "Unclassified": "#7f7f7f",
}
CONFIDENCE_LEVELS = ("high", "medium", "low")
EVIDENCE_DRILLDOWN_METRICS = (
    "revenue",
    "operating_income",
    "net_income",
    "capex",
    "previous_revenue",
    "previous_operating_income",
    "previous_net_income",
)
DEFAULT_FILTER_STATE = {
    "viewer_company_filter": [],
    "viewer_role_filter": [],
    "viewer_confidence_filter": [],
    "viewer_only_comparable": False,
    "viewer_only_warnings": False,
    "viewer_selected_company": "Auto",
}


def load_visualization_dataset(dataset_name: str) -> dict[str, object]:
    dataset_path = VISUALIZATION_DIR / dataset_name
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def _role_label(point: dict[str, object]) -> str:
    roles = point.get("roles", {})
    if not isinstance(roles, dict):
        return "Unclassified"

    active_roles: list[str] = []
    if roles.get("infrastructure_builder") is True:
        active_roles.append("Infrastructure Builder")
    if roles.get("ai_hardware_platform") is True:
        active_roles.append("AI Hardware Platform")
    if roles.get("ai_platform_scale") is True:
        active_roles.append("AI Platform Scale")

    if len(active_roles) > 1:
        return "Multi-Role"
    if active_roles:
        return active_roles[0]
    return "Unclassified"


def _marker_size(point: dict[str, object]) -> float:
    x_value = point.get("x")
    revenue_proxy = point.get("revenue")
    if isinstance(revenue_proxy, (int, float)) and revenue_proxy > 0:
        return max(12.0, min(42.0, revenue_proxy / 25000))
    if isinstance(x_value, (int, float)) and x_value > 1000:
        return max(12.0, min(42.0, x_value / 25000))
    return 16.0


def _confidence_label(point: dict[str, object]) -> str:
    quality = point.get("quality", {})
    if not isinstance(quality, dict):
        return "unknown"
    confidence = quality.get("confidence")
    return confidence if isinstance(confidence, str) else "unknown"


def _warning_text(point: dict[str, object]) -> str:
    quality = point.get("quality", {})
    if not isinstance(quality, dict):
        return "None"
    warnings = quality.get("warnings", [])
    warning_items = [warning for warning in warnings if isinstance(warning, str)]
    return "; ".join(warning_items) if warning_items else "None"


def _filter_points(
    points: list[dict[str, object]],
    *,
    selected_companies: list[str] | None = None,
    selected_roles: list[str] | None = None,
    confidence_levels: list[str] | None = None,
    only_comparable: bool = False,
    only_warnings: bool = False,
) -> list[dict[str, object]]:
    company_filter = set(selected_companies or [])
    role_filter = set(selected_roles or [])
    confidence_filter = set(confidence_levels or [])

    filtered_points: list[dict[str, object]] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        company = point.get("company")
        role = _role_label(point)
        confidence = _confidence_label(point)

        if company_filter and company not in company_filter:
            continue
        if role_filter and role not in role_filter:
            continue
        if confidence_filter and confidence not in confidence_filter:
            continue
        if only_comparable and point.get("comparable") is not True:
            continue
        if only_warnings and _warning_text(point) == "None":
            continue
        filtered_points.append(point)

    return filtered_points


def _format_metric_value(metric_name: str, value: object) -> str:
    if not isinstance(value, (int, float)):
        return "Not available"
    if metric_name in {
        "operating_margin",
        "net_margin",
        "capex_ratio",
        "revenue_growth",
        "operating_income_growth",
        "net_income_growth",
    }:
        return f"{value * 100:.1f}%"
    return f"{value:,.0f}"


def _quality_badge(confidence: str, *, warnings_present: bool = False) -> str:
    if confidence == "high":
        label = "HIGH"
        color = "#2e7d32"
    elif confidence == "medium":
        label = "MEDIUM"
        color = "#f9a825"
    elif confidence == "low":
        label = "LOW"
        color = "#c62828"
    else:
        label = "UNKNOWN"
        color = "#6b7280"

    warning_suffix = " WARN" if warnings_present else ""
    return (
        f"<span style='display:inline-block;padding:0.25rem 0.55rem;border-radius:999px;"
        f"background:{color};color:white;font-size:0.8rem;font-weight:600;'>"
        f"{label}{warning_suffix}</span>"
    )


def _hover_text(point: dict[str, object], *, x_metric: str, y_metric: str) -> str:
    signals = point.get("signals", [])
    signal_text = ", ".join(signal for signal in signals if isinstance(signal, str)) or "None"
    return (
        f"Company: {point.get('company', 'Unknown')}<br>"
        f"Role: {_role_label(point)}<br>"
        f"Confidence: {_confidence_label(point)}<br>"
        f"{x_metric}: {point.get('x', 'N/A')}<br>"
        f"{y_metric}: {point.get('y', 'N/A')}<br>"
        f"Signals: {signal_text}<br>"
        f"Warnings: {_warning_text(point)}"
    )


def build_scatter_figure(
    dataset_payload: dict[str, object],
    *,
    filtered_points: list[dict[str, object]] | None = None,
    highlighted_company: str | None = None,
) -> go.Figure:
    if go is None:
        raise RuntimeError("plotly is required to build the visual intelligence charts.")

    points = filtered_points if filtered_points is not None else dataset_payload.get("points", [])
    x_metric = str(dataset_payload.get("x_metric", "x"))
    y_metric = str(dataset_payload.get("y_metric", "y"))

    grouped_points: dict[str, list[dict[str, object]]] = {}
    for point in points if isinstance(points, list) else []:
        if not isinstance(point, dict):
            continue
        role = _role_label(point)
        grouped_points.setdefault(role, []).append(point)

    figure = go.Figure()
    for role, role_points in grouped_points.items():
        figure.add_trace(
            go.Scatter(
                x=[point.get("x") for point in role_points],
                y=[point.get("y") for point in role_points],
                mode="markers+text",
                name=role,
                text=[point.get("company") for point in role_points],
                textposition="top center",
                marker={
                    "size": [_marker_size(point) for point in role_points],
                    "color": ROLE_COLORS.get(role, ROLE_COLORS["Unclassified"]),
                    "opacity": [
                        1.0 if highlighted_company and point.get("company") == highlighted_company else 0.8
                        for point in role_points
                    ],
                    "line": {
                        "width": [
                            3 if highlighted_company and point.get("company") == highlighted_company else 1
                            for point in role_points
                        ],
                        "color": [
                            "#111827" if highlighted_company and point.get("company") == highlighted_company else "#ffffff"
                            for point in role_points
                        ],
                    },
                },
                hovertemplate="%{customdata}<extra></extra>",
                customdata=[
                    _hover_text(point, x_metric=x_metric, y_metric=y_metric)
                    for point in role_points
                ],
            )
        )

    figure.update_layout(
        title=str(dataset_payload.get("title", "Visualization")),
        xaxis_title=x_metric,
        yaxis_title=y_metric,
        legend_title="Role",
        template="plotly_white",
        height=600,
    )
    return figure


def _ecosystem_summary(dataset_payloads: dict[str, dict[str, object]]) -> tuple[list[str], list[str], list[str]]:
    roles_by_company: dict[str, set[str]] = {}
    for dataset_payload in dataset_payloads.values():
        points = dataset_payload.get("points", [])
        for point in points if isinstance(points, list) else []:
            if not isinstance(point, dict):
                continue
            company = point.get("company")
            if not isinstance(company, str):
                continue
            role = _role_label(point)
            if role == "Unclassified":
                continue
            roles_by_company.setdefault(company, set()).add(role)

    builders = sorted(
        company for company, roles in roles_by_company.items() if "Infrastructure Builder" in roles or "Multi-Role" in roles
    )
    hardware = sorted(
        company for company, roles in roles_by_company.items() if "AI Hardware Platform" in roles or "Multi-Role" in roles
    )
    platforms = sorted(
        company for company, roles in roles_by_company.items() if "AI Platform Scale" in roles or "Multi-Role" in roles
    )
    return builders, hardware, platforms


def _available_companies(dataset_payloads: dict[str, dict[str, object]]) -> list[str]:
    companies: set[str] = set()
    for dataset_payload in dataset_payloads.values():
        points = dataset_payload.get("points", [])
        for point in points if isinstance(points, list) else []:
            if isinstance(point, dict) and isinstance(point.get("company"), str):
                companies.add(point["company"])
    return sorted(companies)


def _available_roles(dataset_payloads: dict[str, dict[str, object]]) -> list[str]:
    roles: set[str] = set()
    for dataset_payload in dataset_payloads.values():
        points = dataset_payload.get("points", [])
        for point in points if isinstance(points, list) else []:
            if isinstance(point, dict):
                roles.add(_role_label(point))
    return sorted(roles)


def _company_options(dataset_payloads: dict[str, dict[str, object]]) -> list[str]:
    return ["Auto", *_available_companies(dataset_payloads)]


def _find_point_by_company(
    dataset_payloads: dict[str, dict[str, object]],
    company: str,
) -> dict[str, object] | None:
    for dataset_payload in dataset_payloads.values():
        points = dataset_payload.get("points", [])
        for point in points if isinstance(points, list) else []:
            if isinstance(point, dict) and point.get("company") == company:
                return point
    return None


def _detail_rows(point: dict[str, object]) -> list[dict[str, str]]:
    metrics = point.get("metrics", {})
    if not isinstance(metrics, dict):
        return []
    ordered_metrics = (
        "revenue",
        "operating_margin",
        "net_margin",
        "capex_ratio",
        "revenue_growth",
        "operating_income_growth",
        "net_income_growth",
    )
    return [
        {
            "Metric": metric_name,
            "Value": _format_metric_value(metric_name, metrics.get(metric_name)),
        }
        for metric_name in ordered_metrics
    ]


def _evidence_preview_rows(point: dict[str, object]) -> list[dict[str, str]]:
    evidence = point.get("evidence", {})
    if not isinstance(evidence, dict):
        return []

    rows: list[dict[str, str]] = []
    for metric_name in (
        "revenue",
        "operating_income",
        "net_income",
        "capex",
    ):
        metric_evidence = evidence.get(metric_name)
        if not isinstance(metric_evidence, dict):
            continue
        source_keyword = metric_evidence.get("source_keyword")
        source_snippet = metric_evidence.get("source_snippet")
        if not isinstance(source_keyword, str) or not isinstance(source_snippet, str):
            continue
        snippet = source_snippet if len(source_snippet) <= 140 else source_snippet[:140] + "..."
        rows.append(
            {
                "Metric": metric_name,
                "Keyword": source_keyword,
                "Snippet": snippet,
            }
        )
    return rows


def _format_evidence_value(metric_name: str, evidence: dict[str, object]) -> str:
    numeric_value = evidence.get("numeric_value")
    unit = evidence.get("unit")
    if not isinstance(numeric_value, (int, float)):
        return "Not available"

    if metric_name in {
        "operating_margin",
        "net_margin",
        "capex_ratio",
        "revenue_growth",
        "operating_income_growth",
        "net_income_growth",
    }:
        formatted = f"{numeric_value * 100:.1f}%"
    else:
        formatted = f"{numeric_value:,.0f}"

    if isinstance(unit, str) and unit:
        return f"{formatted} ({unit})"
    return formatted


def _evidence_drilldown_items(point: dict[str, object]) -> list[dict[str, str]]:
    evidence = point.get("evidence", {})
    if not isinstance(evidence, dict):
        return []

    confidence = _confidence_label(point)
    warnings = _warning_text(point)
    items: list[dict[str, str]] = []
    for metric_name in EVIDENCE_DRILLDOWN_METRICS:
        metric_evidence = evidence.get(metric_name)
        if not isinstance(metric_evidence, dict):
            continue
        if not isinstance(metric_evidence.get("source_snippet"), str):
            continue

        items.append(
            {
                "metric_name": metric_name,
                "extracted_value": _format_evidence_value(metric_name, metric_evidence),
                "confidence": confidence,
                "warnings": warnings,
                "section": str(metric_evidence.get("section") or "Not available"),
                "source_keyword": str(metric_evidence.get("source_keyword") or "Not available"),
                "source_snippet": str(metric_evidence.get("source_snippet") or "Not available"),
                "raw_match": str(metric_evidence.get("raw_match") or "Not available"),
                "unit": str(metric_evidence.get("unit") or "Not available"),
            }
        )

    return items


def _ecosystem_table_rows(dataset_payloads: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for dataset_payload in dataset_payloads.values():
        points = dataset_payload.get("points", [])
        for point in points if isinstance(points, list) else []:
            if not isinstance(point, dict):
                continue
            company = point.get("company")
            if not isinstance(company, str):
                continue
            quality = point.get("quality", {})
            warnings = quality.get("warnings", []) if isinstance(quality, dict) else []
            row = rows.setdefault(
                company,
                {
                    "Company": company,
                    "Infrastructure Builder": False,
                    "AI Hardware Platform": False,
                    "AI Platform Scale": False,
                    "Confidence": _confidence_label(point),
                    "Warnings": "Yes" if isinstance(warnings, list) and warnings else "No",
                },
            )
            roles = point.get("roles", {})
            if isinstance(roles, dict):
                row["Infrastructure Builder"] = row["Infrastructure Builder"] or roles.get("infrastructure_builder") is True
                row["AI Hardware Platform"] = row["AI Hardware Platform"] or roles.get("ai_hardware_platform") is True
                row["AI Platform Scale"] = row["AI Platform Scale"] or roles.get("ai_platform_scale") is True
    return sorted(rows.values(), key=lambda row: str(row["Company"]))


def _reset_filters() -> None:
    if st is None:
        return
    for key, value in DEFAULT_FILTER_STATE.items():
        st.session_state[key] = value


def _initialize_filter_state() -> None:
    if st is None:
        return
    for key, value in DEFAULT_FILTER_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _selected_company_point(
    dataset_payloads: dict[str, dict[str, object]],
    visible_points: list[dict[str, object]],
    selected_company: str,
) -> dict[str, object] | None:
    if selected_company != "Auto":
        return _find_point_by_company(dataset_payloads, selected_company)
    if visible_points:
        return visible_points[0]
    companies = _available_companies(dataset_payloads)
    if not companies:
        return None
    return _find_point_by_company(dataset_payloads, companies[0])


def _render_company_detail_panel(point: dict[str, object]) -> None:
    company = str(point.get("company", "Unknown"))
    quality = point.get("quality", {})
    warnings = quality.get("warnings", []) if isinstance(quality, dict) else []
    notes = quality.get("notes", []) if isinstance(quality, dict) else []
    signals = point.get("signals", [])
    takeaways = point.get("takeaways", [])

    st.markdown("### Company Detail")
    st.markdown(
        _quality_badge(
            _confidence_label(point),
            warnings_present=isinstance(warnings, list) and bool(warnings),
        ),
        unsafe_allow_html=True,
    )
    st.write(company)
    st.table(_detail_rows(point))

    evidence_rows = _evidence_preview_rows(point)
    st.markdown("**Source Evidence Preview**")
    if evidence_rows:
        st.table(evidence_rows)
    else:
        st.write("- None")

    roles = point.get("roles", {})
    active_roles: list[str] = []
    if isinstance(roles, dict):
        if roles.get("infrastructure_builder") is True:
            active_roles.append("Infrastructure Builder")
        if roles.get("ai_hardware_platform") is True:
            active_roles.append("AI Hardware Platform")
        if roles.get("ai_platform_scale") is True:
            active_roles.append("AI Platform Scale")
    st.markdown("**Roles**")
    for role in active_roles or ["None"]:
        st.write(f"- {role}")

    st.markdown("**Signals**")
    for signal in signals if isinstance(signals, list) and signals else ["None"]:
        st.write(f"- {signal}")

    st.markdown("**Takeaways**")
    for takeaway in takeaways if isinstance(takeaways, list) and takeaways else ["None"]:
        st.write(f"- {takeaway}")

    st.markdown("**Notes**")
    for note in notes if isinstance(notes, list) and notes else ["None"]:
        st.write(f"- {note}")

    st.markdown("**Warnings**")
    for warning in warnings if isinstance(warnings, list) and warnings else ["None"]:
        st.write(f"- {warning}")

    drilldown_items = _evidence_drilldown_items(point)
    st.markdown("**Evidence Drill-Down**")
    if not drilldown_items:
        st.write("- None")
        return

    for item in drilldown_items:
        with st.expander(item["metric_name"], expanded=False):
            st.write(f"Extracted value: {item['extracted_value']}")
            st.write(f"Confidence: {item['confidence']}")
            st.write(f"Warnings: {item['warnings']}")
            st.write(f"Filing section: {item['section']}")
            st.write(f"Source keyword: {item['source_keyword']}")
            st.write(f"Raw match: {item['raw_match']}")
            st.write(f"Unit: {item['unit']}")
            st.markdown("Source snippet")
            st.code(item["source_snippet"])


def _filtered_points_json(points: list[dict[str, object]]) -> str:
    return json.dumps(points, indent=2, ensure_ascii=False)


def _filtered_points_csv(points: list[dict[str, object]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "company",
            "role",
            "confidence",
            "warnings",
            "revenue",
            "x",
            "y",
            "signals",
            "comparable",
        ],
    )
    writer.writeheader()
    for point in points:
        if not isinstance(point, dict):
            continue
        writer.writerow(
            {
                "company": point.get("company"),
                "role": _role_label(point),
                "confidence": _confidence_label(point),
                "warnings": _warning_text(point),
                "revenue": point.get("revenue"),
                "x": point.get("x"),
                "y": point.get("y"),
                "signals": ", ".join(
                    signal for signal in point.get("signals", []) if isinstance(signal, str)
                ),
                "comparable": point.get("comparable"),
            }
        )
    return output.getvalue()


def main() -> None:
    if st is None or go is None:
        missing = []
        if st is None:
            missing.append("streamlit")
        if go is None:
            missing.append("plotly")
        raise SystemExit(
            "Missing dependencies for the interactive viewer: " + ", ".join(missing)
        )

    st.set_page_config(page_title="AI Visual Intelligence", layout="wide")
    st.title("AI Visual Intelligence Viewer")
    _initialize_filter_state()

    page = st.sidebar.radio(
        "Page",
        [
            "Profit Pool Map",
            "Growth vs Profit",
            "Infrastructure Map",
            "AI Ecosystem Structure",
        ],
    )
    if st.sidebar.button("Reset Filters", use_container_width=True):
        _reset_filters()
        st.rerun()

    dataset_payloads = {
        page_name: load_visualization_dataset(dataset_file)
        for page_name, dataset_file in DATASET_FILES.items()
    }
    selected_companies = st.sidebar.multiselect(
        "Companies",
        options=_available_companies(dataset_payloads),
        key="viewer_company_filter",
    )
    selected_roles = st.sidebar.multiselect(
        "Roles",
        options=_available_roles(dataset_payloads),
        key="viewer_role_filter",
    )
    selected_confidence = st.sidebar.multiselect(
        "Confidence",
        options=list(CONFIDENCE_LEVELS),
        key="viewer_confidence_filter",
    )
    only_comparable = st.sidebar.toggle(
        "Show Only Comparable Points",
        key="viewer_only_comparable",
    )
    only_warnings = st.sidebar.toggle(
        "Show Only Warning Cases",
        key="viewer_only_warnings",
    )
    selected_company = st.sidebar.selectbox(
        "Company Detail",
        options=_company_options(dataset_payloads),
        key="viewer_selected_company",
    )

    if page in DATASET_FILES:
        dataset_payload = dataset_payloads[page]
        points = dataset_payload.get("points", [])
        filtered_points = _filter_points(
            points if isinstance(points, list) else [],
            selected_companies=selected_companies,
            selected_roles=selected_roles,
            confidence_levels=selected_confidence,
            only_comparable=only_comparable,
            only_warnings=only_warnings,
        )
        st.subheader(page)
        st.caption(
            f"Source: {DATASET_FILES[page]} | Filing year: {dataset_payload.get('filing_year', 'unknown')}"
        )
        st.caption(f"Visible points: {len(filtered_points)} / {len(points) if isinstance(points, list) else 0}")
        chart_col, detail_col = st.columns([2.2, 1.1])
        with chart_col:
            st.plotly_chart(
                build_scatter_figure(
                    dataset_payload,
                    filtered_points=filtered_points,
                    highlighted_company=None if selected_company == "Auto" else selected_company,
                ),
                use_container_width=True,
            )
            st.download_button(
                "Download Filtered Points JSON",
                data=_filtered_points_json(filtered_points),
                file_name=f"{dataset_payload.get('dataset', 'dataset')}_filtered.json",
                mime="application/json",
                use_container_width=True,
            )
            st.download_button(
                "Download Filtered Points CSV",
                data=_filtered_points_csv(filtered_points),
                file_name=f"{dataset_payload.get('dataset', 'dataset')}_filtered.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with detail_col:
            selected_point = _selected_company_point(
                dataset_payloads,
                filtered_points,
                selected_company,
            )
            if selected_point is not None:
                _render_company_detail_panel(selected_point)
            else:
                st.info("No company matches the current filters.")

        with st.expander("Underlying data points", expanded=False):
            st.json(filtered_points)
        return

    filtered_dataset_payloads = {
        page_name: {
            **dataset_payload,
            "points": _filter_points(
                dataset_payload.get("points", []) if isinstance(dataset_payload.get("points", []), list) else [],
                selected_companies=selected_companies,
                selected_roles=selected_roles,
                confidence_levels=selected_confidence,
                only_comparable=only_comparable,
                only_warnings=only_warnings,
            ),
        }
        for page_name, dataset_payload in dataset_payloads.items()
    }
    builders, hardware, platforms = _ecosystem_summary(filtered_dataset_payloads)
    st.subheader("AI Ecosystem Structure")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Infrastructure Builders**")
        for company in builders or ["None identified"]:
            st.write(f"- {company}")
    with col2:
        st.markdown("**AI Hardware Platforms**")
        for company in hardware or ["None identified"]:
            st.write(f"- {company}")
    with col3:
        st.markdown("**AI Platform Scale**")
        for company in platforms or ["None identified"]:
            st.write(f"- {company}")

    st.markdown("### Ecosystem Table")
    st.table(_ecosystem_table_rows(filtered_dataset_payloads))

    st.markdown("**Role color legend**")
    for role, color in ROLE_COLORS.items():
        st.markdown(f"- `{role}`: `{color}`")


if __name__ == "__main__":
    main()
