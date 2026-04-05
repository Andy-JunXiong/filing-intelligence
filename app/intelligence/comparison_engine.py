from __future__ import annotations

import json
from pathlib import Path

from app.quality import build_data_quality_notes, merge_company_quality


COMPARISONS_OUTPUT_DIR = Path("data") / "comparisons"
COMPARISON_METRICS = (
    "revenue",
    "operating_margin",
    "net_margin",
    "capex_ratio",
    "revenue_growth",
    "operating_income_growth",
    "net_income_growth",
)
METRIC_TITLES = {
    "revenue": "Revenue",
    "operating_margin": "Operating Margin",
    "net_margin": "Net Margin",
    "capex_ratio": "Capex Ratio",
    "revenue_growth": "Revenue Growth",
    "operating_income_growth": "Operating Income Growth",
    "net_income_growth": "Net Income Growth",
}
MULTI_COMPANY_DEFAULT_LABEL = "AI_sector"
AI_INFRASTRUCTURE_LABELS = (
    "AI Infrastructure Builder",
    "AI Hardware Platform",
    "AI Platform Scale",
)
EVIDENCE_METRICS = (
    "revenue",
    "operating_income",
    "net_income",
    "capex",
    "previous_revenue",
    "previous_operating_income",
    "previous_net_income",
)


def _get_filing_year(payload: dict[str, object]) -> str | None:
    filing_date = payload.get("filing_date")
    if not isinstance(filing_date, str) or len(filing_date) < 4:
        return None
    return filing_date[:4]


def _get_extracted_numeric(
    extracted_payload: dict[str, object],
    metric_name: str,
) -> int | float | None:
    financial_metrics = extracted_payload.get("financial_metrics", {})
    if not isinstance(financial_metrics, dict):
        return None
    metric = financial_metrics.get(metric_name)
    if not isinstance(metric, dict):
        return None
    value = metric.get("numeric_value")
    return value if isinstance(value, (int, float)) else None


def _get_signal_metric(
    signals_payload: dict[str, object],
    metric_name: str,
) -> float | None:
    metrics = signals_payload.get("metrics", {})
    if not isinstance(metrics, dict):
        return None
    value = metrics.get(metric_name)
    return value if isinstance(value, (int, float)) else None


def _get_metric_evidence(
    extracted_payload: dict[str, object],
    metric_name: str,
) -> dict[str, object] | None:
    financial_metrics = extracted_payload.get("financial_metrics", {})
    if not isinstance(financial_metrics, dict):
        return None
    metric = financial_metrics.get(metric_name)
    if not isinstance(metric, dict):
        return None

    evidence = {
        "numeric_value": metric.get("numeric_value"),
        "unit": metric.get("unit"),
        "source_keyword": metric.get("source_keyword"),
        "source_snippet": metric.get("source_snippet"),
        "section": metric.get("section"),
        "raw_match": metric.get("raw_match"),
    }
    return evidence


def _collect_company_evidence(
    extracted_payload: dict[str, object],
) -> dict[str, dict[str, object] | None]:
    return {
        metric_name: _get_metric_evidence(extracted_payload, metric_name)
        for metric_name in EVIDENCE_METRICS
    }


def _build_metric_comparison(
    left_label: str,
    left_value: int | float | None,
    right_label: str,
    right_value: int | float | None,
) -> dict[str, object]:
    if left_value is None or right_value is None:
        winner = None
    elif left_value > right_value:
        winner = left_label
    elif right_value > left_value:
        winner = right_label
    else:
        winner = "equal"

    return {
        left_label: left_value,
        right_label: right_value,
        "higher": winner,
        "comparable": left_value is not None and right_value is not None,
    }


def _signal_labels(signals_payload: dict[str, object]) -> list[str]:
    raw_signals = signals_payload.get("signals", [])
    labels: list[str] = []
    if not isinstance(raw_signals, list):
        return labels

    for signal in raw_signals:
        if not isinstance(signal, dict):
            continue
        label = signal.get("signal")
        if isinstance(label, str):
            labels.append(label)

    return labels


def _build_ai_infrastructure_landscape(
    signals_by_company: dict[str, list[str]],
) -> dict[str, list[str]]:
    landscape = {
        "infrastructure_builders": [],
        "ai_hardware_platforms": [],
        "ai_platform_scale_leaders": [],
    }

    for company, labels in signals_by_company.items():
        if "AI Infrastructure Builder" in labels:
            landscape["infrastructure_builders"].append(company)
        if "AI Hardware Platform" in labels:
            landscape["ai_hardware_platforms"].append(company)
        if "AI Platform Scale" in labels:
            landscape["ai_platform_scale_leaders"].append(company)

    return landscape


def _takeaway_for_metric(
    metric_name: str,
    comparison: dict[str, object],
) -> str | None:
    higher = comparison.get("higher")
    if higher in (None, "equal"):
        return None

    if metric_name == "operating_margin":
        return f"{higher} shows the stronger operating profitability."
    if metric_name == "capex_ratio":
        return f"{higher} shows higher infrastructure investment intensity relative to revenue."
    if metric_name == "revenue":
        return f"{higher} reports the higher revenue in the selected filing year."
    if metric_name == "net_margin":
        return f"{higher} shows the stronger net profitability."
    if metric_name == "revenue_growth":
        return f"{higher} shows the stronger revenue growth."
    if metric_name == "operating_income_growth":
        return f"{higher} shows the stronger operating income growth."
    if metric_name == "net_income_growth":
        return f"{higher} shows the stronger net income growth."
    return None


def _build_non_comparable_fields(metrics: dict[str, dict[str, object]]) -> list[str]:
    not_comparable: list[str] = []
    for metric_name in COMPARISON_METRICS:
        metric_payload = metrics.get(metric_name, {})
        if not isinstance(metric_payload, dict):
            not_comparable.append(metric_name)
            continue
        if metric_payload.get("comparable") is not True:
            not_comparable.append(metric_name)
    return not_comparable


def _format_metric_value(metric_name: str, value: int | float | None) -> str:
    if value is None:
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


def _build_metric_observation(metric_name: str, metric_payload: dict[str, object]) -> str:
    higher = metric_payload.get("higher")
    if higher is None:
        return f"{METRIC_TITLES[metric_name]} is not fully comparable because one or both values are missing."
    if higher == "equal":
        return f"{METRIC_TITLES[metric_name]} is broadly aligned between the two companies."

    if metric_name == "revenue":
        return f"{higher} reports the larger revenue base in the selected filing year."
    if metric_name == "operating_margin":
        return f"{higher} converts revenue into operating profit more efficiently."
    if metric_name == "net_margin":
        return f"{higher} retains a larger share of revenue as net income."
    if metric_name == "capex_ratio":
        return f"{higher} is deploying a larger share of revenue into infrastructure-related investment."
    if metric_name == "revenue_growth":
        return f"{higher} is growing revenue faster year over year."
    if metric_name == "operating_income_growth":
        return f"{higher} is growing operating income faster year over year."
    if metric_name == "net_income_growth":
        return f"{higher} is growing net income faster year over year."

    return f"{higher} leads on {metric_name}."


def _build_summary_sentence(
    left_label: str,
    right_label: str,
    metrics: dict[str, dict[str, object]],
) -> str:
    summary_parts: list[str] = []
    revenue_leader = metrics["revenue"].get("higher")
    operating_margin_leader = metrics["operating_margin"].get("higher")
    capex_ratio_leader = metrics["capex_ratio"].get("higher")
    revenue_growth_leader = metrics["revenue_growth"].get("higher")

    if revenue_leader not in (None, "equal"):
        summary_parts.append(f"{revenue_leader} is larger on revenue")
    if operating_margin_leader not in (None, "equal"):
        summary_parts.append(f"{operating_margin_leader} is stronger on operating margin")
    if capex_ratio_leader not in (None, "equal"):
        summary_parts.append(f"{capex_ratio_leader} is higher on capex intensity")
    if revenue_growth_leader not in (None, "equal"):
        summary_parts.append(f"{revenue_growth_leader} is faster on revenue growth")

    if not summary_parts:
        return f"{left_label} and {right_label} remain only partially comparable on the current metric set."

    return "; ".join(summary_parts).capitalize() + "."


def _build_company_snapshot(
    extracted_payload: dict[str, object],
    signals_payload: dict[str, object],
    insight_payload: dict[str, object],
) -> dict[str, object]:
    company = str(extracted_payload.get("ticker") or extracted_payload.get("company"))
    return {
        "company": company,
        "filing_type": extracted_payload.get("filing_type"),
        "filing_date": extracted_payload.get("filing_date"),
        "metrics": {
            "revenue": _get_extracted_numeric(extracted_payload, "revenue"),
            "operating_margin": _get_signal_metric(signals_payload, "operating_margin"),
            "net_margin": _get_signal_metric(signals_payload, "net_margin"),
            "capex_ratio": _get_signal_metric(signals_payload, "capex_ratio"),
            "revenue_growth": _get_signal_metric(signals_payload, "revenue_growth"),
            "operating_income_growth": _get_signal_metric(signals_payload, "operating_income_growth"),
            "net_income_growth": _get_signal_metric(signals_payload, "net_income_growth"),
        },
        "signals": _signal_labels(signals_payload),
        "insights": insight_payload.get("takeaways", []),
        "quality": merge_company_quality(company, extracted_payload, signals_payload),
        "evidence": _collect_company_evidence(extracted_payload),
    }


def _sort_ranking_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    available = [
        entry for entry in entries if isinstance(entry.get("value"), (int, float))
    ]
    missing = [
        entry for entry in entries if not isinstance(entry.get("value"), (int, float))
    ]
    available.sort(key=lambda entry: float(entry["value"]), reverse=True)

    ranked_entries: list[dict[str, object]] = []
    for index, entry in enumerate(available, start=1):
        ranked_entries.append(
            {
                "rank": index,
                "company": entry["company"],
                "value": entry["value"],
            }
        )

    for entry in missing:
        ranked_entries.append(
            {
                "rank": None,
                "company": entry["company"],
                "value": None,
            }
        )

    return ranked_entries


def _build_multi_company_rankings(
    company_snapshots: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    rankings: dict[str, dict[str, object]] = {}
    for metric_name in COMPARISON_METRICS:
        ranking_entries = _sort_ranking_entries(
            [
                {
                    "company": str(snapshot["company"]),
                    "value": snapshot["metrics"].get(metric_name)
                    if isinstance(snapshot.get("metrics"), dict)
                    else None,
                }
                for snapshot in company_snapshots
            ]
        )
        available_values = [
            entry["value"] for entry in ranking_entries if isinstance(entry.get("value"), (int, float))
        ]
        rankings[metric_name] = {
            "ranking": ranking_entries,
            "leader": ranking_entries[0]["company"] if available_values else None,
            "comparable_company_count": len(available_values),
        }
    return rankings


def _build_multi_company_non_comparable_fields(
    rankings: dict[str, dict[str, object]],
    company_count: int,
) -> list[str]:
    non_comparable_fields: list[str] = []
    for metric_name in COMPARISON_METRICS:
        comparable_count = rankings.get(metric_name, {}).get("comparable_company_count")
        if comparable_count != company_count:
            non_comparable_fields.append(metric_name)
    return non_comparable_fields


def _build_multi_company_takeaways(
    *,
    same_filing_year: bool,
    rankings: dict[str, dict[str, object]],
    non_comparable_fields: list[str],
) -> list[str]:
    if not same_filing_year:
        return []

    takeaways: list[str] = []
    revenue_leader = rankings["revenue"].get("leader")
    operating_margin_leader = rankings["operating_margin"].get("leader")
    capex_ratio_leader = rankings["capex_ratio"].get("leader")
    revenue_growth_leader = rankings["revenue_growth"].get("leader")
    net_income_growth_leader = rankings["net_income_growth"].get("leader")

    if operating_margin_leader is not None:
        takeaways.append(
            f"{operating_margin_leader} demonstrates the highest operating profitability among the selected companies."
        )
    if capex_ratio_leader is not None:
        takeaways.append(
            f"{capex_ratio_leader} shows the highest infrastructure investment intensity relative to revenue."
        )
    if revenue_leader is not None:
        takeaways.append(
            f"{revenue_leader} reports the largest revenue among the selected companies."
        )
    if revenue_growth_leader is not None:
        takeaways.append(
            f"{revenue_growth_leader} demonstrates the strongest revenue growth among the selected companies."
        )
    if net_income_growth_leader is not None:
        takeaways.append(
            f"{net_income_growth_leader} shows the strongest net income growth momentum."
        )
    if non_comparable_fields:
        takeaways.append(
            "Not fully comparable: " + ", ".join(non_comparable_fields) + "."
        )

    return takeaways[:5]


def _build_multi_company_summary(rankings: dict[str, dict[str, object]]) -> str:
    summary_parts: list[str] = []
    revenue_leader = rankings["revenue"].get("leader")
    operating_margin_leader = rankings["operating_margin"].get("leader")
    capex_ratio_leader = rankings["capex_ratio"].get("leader")
    revenue_growth_leader = rankings["revenue_growth"].get("leader")

    if revenue_leader is not None:
        summary_parts.append(f"{revenue_leader} leads on revenue")
    if operating_margin_leader is not None:
        summary_parts.append(f"{operating_margin_leader} leads on operating margin")
    if capex_ratio_leader is not None:
        summary_parts.append(f"{capex_ratio_leader} leads on capex intensity")
    if revenue_growth_leader is not None:
        summary_parts.append(f"{revenue_growth_leader} leads on revenue growth")

    if not summary_parts:
        return "The selected companies remain only partially comparable on the current metric set."

    return "; ".join(summary_parts).capitalize() + "."


def _build_ranking_observation(
    metric_name: str,
    ranking_payload: dict[str, object],
    company_count: int,
) -> str:
    leader = ranking_payload.get("leader")
    comparable_company_count = ranking_payload.get("comparable_company_count")
    if leader is None:
        return f"{METRIC_TITLES[metric_name]} is not comparable because no valid values were extracted."
    if comparable_company_count != company_count:
        return f"{leader} leads on {METRIC_TITLES[metric_name].lower()}, but coverage is incomplete across the selected companies."
    return f"{leader} ranks first on {METRIC_TITLES[metric_name].lower()} across the selected companies."


def _build_takeaways(
    *,
    filing_years_match: bool,
    metrics: dict[str, dict[str, object]],
) -> list[str]:
    if not filing_years_match:
        return []

    takeaways: list[str] = []
    for metric_name in ("operating_margin", "capex_ratio", "revenue"):
        takeaway = _takeaway_for_metric(metric_name, metrics[metric_name])
        if takeaway is not None:
            takeaways.append(takeaway)
    for metric_name in ("revenue_growth", "net_income_growth"):
        takeaway = _takeaway_for_metric(metric_name, metrics[metric_name])
        if takeaway is not None:
            takeaways.append(takeaway)

    non_comparable_fields = _build_non_comparable_fields(metrics)
    if non_comparable_fields:
        takeaways.append(
            "Not fully comparable: " + ", ".join(non_comparable_fields) + "."
        )

    return takeaways[:5]


def build_company_comparison(
    left_extracted: dict[str, object],
    left_signals: dict[str, object],
    left_insight: dict[str, object],
    right_extracted: dict[str, object],
    right_signals: dict[str, object],
    right_insight: dict[str, object],
) -> dict[str, object]:
    left_label = str(left_extracted.get("ticker") or left_extracted.get("company"))
    right_label = str(right_extracted.get("ticker") or right_extracted.get("company"))
    filing_type = str(left_extracted.get("filing_type") or right_extracted.get("filing_type"))

    left_year = _get_filing_year(left_extracted)
    right_year = _get_filing_year(right_extracted)
    filing_years_match = left_year is not None and left_year == right_year
    comparison_filing_year = left_year if filing_years_match else None

    metrics = {
        "revenue": _build_metric_comparison(
            left_label,
            _get_extracted_numeric(left_extracted, "revenue"),
            right_label,
            _get_extracted_numeric(right_extracted, "revenue"),
        ),
        "operating_margin": _build_metric_comparison(
            left_label,
            _get_signal_metric(left_signals, "operating_margin"),
            right_label,
            _get_signal_metric(right_signals, "operating_margin"),
        ),
        "net_margin": _build_metric_comparison(
            left_label,
            _get_signal_metric(left_signals, "net_margin"),
            right_label,
            _get_signal_metric(right_signals, "net_margin"),
        ),
        "capex_ratio": _build_metric_comparison(
            left_label,
            _get_signal_metric(left_signals, "capex_ratio"),
            right_label,
            _get_signal_metric(right_signals, "capex_ratio"),
        ),
        "revenue_growth": _build_metric_comparison(
            left_label,
            _get_signal_metric(left_signals, "revenue_growth"),
            right_label,
            _get_signal_metric(right_signals, "revenue_growth"),
        ),
        "operating_income_growth": _build_metric_comparison(
            left_label,
            _get_signal_metric(left_signals, "operating_income_growth"),
            right_label,
            _get_signal_metric(right_signals, "operating_income_growth"),
        ),
        "net_income_growth": _build_metric_comparison(
            left_label,
            _get_signal_metric(left_signals, "net_income_growth"),
            right_label,
            _get_signal_metric(right_signals, "net_income_growth"),
        ),
    }

    comparison = {
        "companies": [left_label, right_label],
        "filing_type": filing_type,
        "filing_year": comparison_filing_year,
        "filing_dates": {
            left_label: left_extracted.get("filing_date"),
            right_label: right_extracted.get("filing_date"),
        },
        "comparability": {
            "same_filing_year": filing_years_match,
            "non_comparable_fields": _build_non_comparable_fields(metrics),
        },
        "metrics": metrics,
        "signals": {
            left_label: _signal_labels(left_signals),
            right_label: _signal_labels(right_signals),
        },
        "insights": {
            left_label: left_insight.get("takeaways", []),
            right_label: right_insight.get("takeaways", []),
        },
        "quality": {
            left_label: merge_company_quality(left_label, left_extracted, left_signals),
            right_label: merge_company_quality(right_label, right_extracted, right_signals),
        },
        "evidence": {
            left_label: _collect_company_evidence(left_extracted),
            right_label: _collect_company_evidence(right_extracted),
        },
        "takeaways": _build_takeaways(
            filing_years_match=filing_years_match,
            metrics=metrics,
        ),
    }
    comparison["ai_infrastructure_landscape"] = _build_ai_infrastructure_landscape(
        comparison["signals"]
    )
    return comparison


def build_multi_company_comparison(
    company_payloads: list[dict[str, object]],
) -> dict[str, object]:
    if len(company_payloads) < 2:
        raise ValueError("Multi-company comparison requires at least two companies.")

    company_snapshots = [
        _build_company_snapshot(
            payload["extracted_payload"],
            payload["signals_payload"],
            payload["insight_payload"],
        )
        for payload in company_payloads
    ]

    filing_type = str(company_snapshots[0].get("filing_type") or "unknown")
    filing_years = [
        _get_filing_year({"filing_date": snapshot.get("filing_date")})
        for snapshot in company_snapshots
    ]
    valid_filing_years = [year for year in filing_years if year is not None]
    same_filing_year = len(valid_filing_years) == len(company_snapshots) and len(set(valid_filing_years)) == 1
    filing_year = valid_filing_years[0] if same_filing_year else None

    rankings = _build_multi_company_rankings(company_snapshots)
    non_comparable_fields = _build_multi_company_non_comparable_fields(
        rankings,
        company_count=len(company_snapshots),
    )

    comparison = {
        "companies": [str(snapshot["company"]) for snapshot in company_snapshots],
        "filing_type": filing_type,
        "filing_year": filing_year,
        "filing_dates": {
            str(snapshot["company"]): snapshot.get("filing_date")
            for snapshot in company_snapshots
        },
        "comparability": {
            "same_filing_year": same_filing_year,
            "non_comparable_fields": non_comparable_fields,
        },
        "rankings": rankings,
        "signals": {
            str(snapshot["company"]): snapshot.get("signals", [])
            for snapshot in company_snapshots
        },
        "insights": {
            str(snapshot["company"]): snapshot.get("insights", [])
            for snapshot in company_snapshots
        },
        "quality": {
            str(snapshot["company"]): snapshot.get("quality", {})
            for snapshot in company_snapshots
        },
        "evidence": {
            str(snapshot["company"]): snapshot.get("evidence", {})
            for snapshot in company_snapshots
        },
        "takeaways": _build_multi_company_takeaways(
            same_filing_year=same_filing_year,
            rankings=rankings,
            non_comparable_fields=non_comparable_fields,
        ),
        "summary": _build_multi_company_summary(rankings),
    }
    comparison["ai_infrastructure_landscape"] = _build_ai_infrastructure_landscape(
        comparison["signals"]
    )
    return comparison


def export_company_comparison(
    comparison_payload: dict[str, object],
    output_dir: Path = COMPARISONS_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    companies = comparison_payload.get("companies", ["left", "right"])
    left_label = str(companies[0])
    right_label = str(companies[1])
    filing_type = str(comparison_payload.get("filing_type", "unknown"))
    filing_year = str(comparison_payload.get("filing_year", "unknown"))
    output_path = output_dir / f"{left_label}_vs_{right_label}_{filing_type}_{filing_year}.json"
    output_path.write_text(
        json.dumps(comparison_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def export_company_comparison_markdown(
    comparison_payload: dict[str, object],
    output_dir: Path = COMPARISONS_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    companies = comparison_payload.get("companies", ["left", "right"])
    left_label = str(companies[0])
    right_label = str(companies[1])
    filing_type = str(comparison_payload.get("filing_type", "unknown"))
    filing_year = str(comparison_payload.get("filing_year", "unknown"))
    output_path = output_dir / f"{left_label}_vs_{right_label}_{filing_type}_{filing_year}.md"

    filing_dates = comparison_payload.get("filing_dates", {})
    comparability = comparison_payload.get("comparability", {})
    metrics = comparison_payload.get("metrics", {})
    signals = comparison_payload.get("signals", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    takeaways = comparison_payload.get("takeaways", [])
    quality = comparison_payload.get("quality", {})
    same_filing_year = comparability.get("same_filing_year") if isinstance(comparability, dict) else False
    non_comparable_fields = (
        comparability.get("non_comparable_fields", [])
        if isinstance(comparability, dict)
        else []
    )

    lines = [
        "# Financial Comparison",
        f"{left_label} vs {right_label} ({filing_type} {filing_year})",
        "",
        "## Summary",
    ]

    if isinstance(metrics, dict):
        lines.append(f"- {_build_summary_sentence(left_label, right_label, metrics)}")
    if same_filing_year:
        lines.append(
            f"- Filing-year scope is aligned: {left_label}={filing_dates.get(left_label) if isinstance(filing_dates, dict) else 'unknown'}, "
            f"{right_label}={filing_dates.get(right_label) if isinstance(filing_dates, dict) else 'unknown'}."
        )
    else:
        lines.append(
            f"- Filing-year scope is not aligned: {left_label}={filing_dates.get(left_label) if isinstance(filing_dates, dict) else 'unknown'}, "
            f"{right_label}={filing_dates.get(right_label) if isinstance(filing_dates, dict) else 'unknown'}."
        )
    if isinstance(takeaways, list) and takeaways:
        for takeaway in takeaways[:4]:
            lines.append(f"- {takeaway}")
    elif same_filing_year:
        lines.append("- No additional rule-based takeaways were generated.")
    else:
        lines.append("- Final comparison takeaways are withheld because the filing years do not match.")

    for metric_name in COMPARISON_METRICS:
        metric_payload = metrics.get(metric_name, {}) if isinstance(metrics, dict) else {}
        if not isinstance(metric_payload, dict):
            continue

        lines.extend(
            [
                "",
                f"## {METRIC_TITLES[metric_name]}",
                f"- {left_label}: {_format_metric_value(metric_name, metric_payload.get(left_label))}",
                f"- {right_label}: {_format_metric_value(metric_name, metric_payload.get(right_label))}",
                f"- Observation: {_build_metric_observation(metric_name, metric_payload)}",
            ]
        )

    lines.extend(["", "## Signals Comparison"])
    if isinstance(signals, dict):
        for company in (left_label, right_label):
            company_signals = signals.get(company, [])
            lines.append(f"### {company}")
            if isinstance(company_signals, list) and company_signals:
                for signal in company_signals:
                    lines.append(f"- {signal}")
            else:
                lines.append("- None")

    lines.extend(["", "## AI Infrastructure Landscape"])
    if isinstance(ai_landscape, dict):
        builders = ai_landscape.get("infrastructure_builders", [])
        hardware = ai_landscape.get("ai_hardware_platforms", [])
        scale_leaders = ai_landscape.get("ai_platform_scale_leaders", [])
        lines.append(
            f"- Infrastructure Builders: {', '.join(builders) if builders else 'None'}"
        )
        lines.append(
            f"- AI Hardware Platforms: {', '.join(hardware) if hardware else 'None'}"
        )
        lines.append(
            f"- AI Platform Scale Leaders: {', '.join(scale_leaders) if scale_leaders else 'None'}"
        )

    lines.extend(["", "## Data Quality Notes"])
    if isinstance(quality, dict):
        for note in build_data_quality_notes(quality):
            lines.append(f"- {note}")
    else:
        lines.append("- Quality metadata is not available for the current comparison set.")

    lines.extend(["", "## Final Takeaways"])
    if isinstance(takeaways, list) and takeaways:
        for takeaway in takeaways:
            lines.append(f"- {takeaway}")
    elif same_filing_year:
        if non_comparable_fields:
            lines.append("- Comparison remains partial because some metrics are missing.")
        else:
            lines.append("- No rule-based final takeaways were generated.")
    else:
        lines.append("- Comparison takeaways are not produced when filing years differ.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def export_multi_company_comparison(
    comparison_payload: dict[str, object],
    output_dir: Path = COMPARISONS_OUTPUT_DIR,
    comparison_label: str = MULTI_COMPANY_DEFAULT_LABEL,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filing_type = str(comparison_payload.get("filing_type", "unknown"))
    filing_year = str(comparison_payload.get("filing_year", "unknown"))
    output_path = output_dir / f"{comparison_label}_{filing_type}_{filing_year}.json"
    output_path.write_text(
        json.dumps(comparison_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def export_multi_company_comparison_markdown(
    comparison_payload: dict[str, object],
    output_dir: Path = COMPARISONS_OUTPUT_DIR,
    comparison_label: str = MULTI_COMPANY_DEFAULT_LABEL,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filing_type = str(comparison_payload.get("filing_type", "unknown"))
    filing_year = str(comparison_payload.get("filing_year", "unknown"))
    output_path = output_dir / f"{comparison_label}_{filing_type}_{filing_year}.md"

    companies = comparison_payload.get("companies", [])
    filing_dates = comparison_payload.get("filing_dates", {})
    comparability = comparison_payload.get("comparability", {})
    rankings = comparison_payload.get("rankings", {})
    signals = comparison_payload.get("signals", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    takeaways = comparison_payload.get("takeaways", [])
    summary = comparison_payload.get("summary", "")
    quality = comparison_payload.get("quality", {})
    same_filing_year = comparability.get("same_filing_year") if isinstance(comparability, dict) else False

    lines = [
        "# Multi-Company Financial Comparison",
        f"{', '.join(companies)} ({filing_type} {filing_year})",
        "",
        "## Filing Scope",
    ]

    for company in companies:
        lines.append(
            f"- {company}: {filing_dates.get(company) if isinstance(filing_dates, dict) else 'unknown'}"
        )
    lines.append(f"- same_filing_year: {same_filing_year}")

    lines.extend(["", "## Summary"])
    if isinstance(summary, str) and summary:
        lines.append(f"- {summary}")
    if isinstance(takeaways, list) and takeaways:
        for takeaway in takeaways[:4]:
            lines.append(f"- {takeaway}")
    elif same_filing_year:
        lines.append("- No additional rule-based takeaways were generated.")
    else:
        lines.append("- Key takeaways are withheld because the filing years do not match.")

    for metric_name in COMPARISON_METRICS:
        ranking_payload = rankings.get(metric_name, {}) if isinstance(rankings, dict) else {}
        ranking_entries = ranking_payload.get("ranking", []) if isinstance(ranking_payload, dict) else []
        lines.extend(["", f"## {METRIC_TITLES[metric_name]} Ranking"])
        for entry in ranking_entries:
            if not isinstance(entry, dict):
                continue
            rank = entry.get("rank")
            company = entry.get("company")
            value = entry.get("value")
            rank_label = f"{rank}." if isinstance(rank, int) else "- "
            lines.append(
                f"{rank_label} {company}: {_format_metric_value(metric_name, value if isinstance(value, (int, float)) else None)}"
            )
        if isinstance(ranking_payload, dict):
            lines.append(
                f"- Observation: {_build_ranking_observation(metric_name, ranking_payload, len(companies))}"
            )

    lines.extend(["", "## Signals by Company"])
    if isinstance(signals, dict):
        for company in companies:
            lines.append(f"### {company}")
            company_signals = signals.get(company, [])
            if isinstance(company_signals, list) and company_signals:
                for signal in company_signals:
                    lines.append(f"- {signal}")
            else:
                lines.append("- None")

    lines.extend(["", "## AI Infrastructure Landscape"])
    if isinstance(ai_landscape, dict):
        builders = ai_landscape.get("infrastructure_builders", [])
        hardware = ai_landscape.get("ai_hardware_platforms", [])
        scale_leaders = ai_landscape.get("ai_platform_scale_leaders", [])
        lines.append(
            f"- Infrastructure Builders: {', '.join(builders) if builders else 'None'}"
        )
        lines.append(
            f"- AI Hardware Platforms: {', '.join(hardware) if hardware else 'None'}"
        )
        lines.append(
            f"- AI Platform Scale Leaders: {', '.join(scale_leaders) if scale_leaders else 'None'}"
        )

    lines.extend(["", "## Data Quality Notes"])
    if isinstance(quality, dict):
        for note in build_data_quality_notes(quality):
            lines.append(f"- {note}")
    else:
        lines.append("- Quality metadata is not available for the current comparison set.")

    lines.extend(["", "## Key Takeaways"])
    if isinstance(takeaways, list) and takeaways:
        for takeaway in takeaways:
            lines.append(f"- {takeaway}")
    elif same_filing_year:
        lines.append("- No rule-based multi-company takeaways were generated.")
    else:
        lines.append("- Multi-company takeaways are not produced when filing years differ.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
