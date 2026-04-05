from __future__ import annotations

from pathlib import Path


TRAJECTORIES_OUTPUT_DIR = Path("data") / "trajectories"
TRAJECTORY_METRICS = (
    "revenue",
    "operating_margin",
    "net_margin",
    "capex_ratio",
    "revenue_growth",
)
TRAJECTORY_TITLES = {
    "revenue": "Revenue",
    "operating_margin": "Operating Margin",
    "net_margin": "Net Margin",
    "capex_ratio": "Capex Ratio",
    "revenue_growth": "Revenue Growth",
}


def _metric_value(payload: dict[str, object], metric_name: str) -> int | float | None:
    if metric_name == "revenue":
        financial_metrics = payload.get("extracted_payload", {}).get("financial_metrics", {})
        if isinstance(financial_metrics, dict):
            metric = financial_metrics.get("revenue")
            if isinstance(metric, dict):
                value = metric.get("numeric_value")
                if isinstance(value, (int, float)):
                    return value
        return None

    metrics = payload.get("signals_payload", {}).get("metrics", {})
    if not isinstance(metrics, dict):
        return None
    value = metrics.get(metric_name)
    return value if isinstance(value, (int, float)) else None


def _format_metric(metric_name: str, value: int | float | None) -> str:
    if value is None:
        return "Not available"
    if metric_name in {"operating_margin", "net_margin", "capex_ratio", "revenue_growth"}:
        return f"{value * 100:.1f}%"
    return f"{value:,.0f}"


def _trajectory_direction(values: list[int | float | None]) -> str:
    valid_values = [value for value in values if isinstance(value, (int, float))]
    if len(valid_values) < 2:
        return "insufficient_data"
    if valid_values[0] < valid_values[-1] and all(
        earlier <= later for earlier, later in zip(valid_values, valid_values[1:])
    ):
        return "up"
    if valid_values[0] > valid_values[-1] and all(
        earlier >= later for earlier, later in zip(valid_values, valid_values[1:])
    ):
        return "down"
    return "mixed"


def _build_revenue_trajectory(company: str, yearly_payloads: list[dict[str, object]]) -> str:
    revenue_growth_values = [_metric_value(payload, "revenue_growth") for payload in yearly_payloads]
    revenue_values = [_metric_value(payload, "revenue") for payload in yearly_payloads]
    direction = _trajectory_direction(revenue_values)

    if all(isinstance(value, (int, float)) and value > 0.20 for value in revenue_growth_values[-2:]):
        return f"{company} demonstrates sustained revenue acceleration across the past three filings."
    if direction == "up":
        return f"{company} shows a consistent upward revenue trajectory across the selected filings."
    if direction == "down":
        return f"{company} shows a declining revenue trajectory across the selected filings."
    return f"{company} shows a mixed revenue trajectory across the selected filings."


def _build_margin_expansion(company: str, yearly_payloads: list[dict[str, object]]) -> str:
    operating_margin_values = [_metric_value(payload, "operating_margin") for payload in yearly_payloads]
    direction = _trajectory_direction(operating_margin_values)
    latest_growth = _metric_value(yearly_payloads[-1], "revenue_growth")

    if direction == "up" and isinstance(latest_growth, (int, float)) and latest_growth > 0.20:
        return f"{company} shows significant margin expansion driven by AI demand."
    if direction == "up":
        return f"{company} shows margin expansion across the selected filings."
    if direction == "down":
        return f"{company} shows margin compression across the selected filings."
    return f"{company} shows a mixed margin profile across the selected filings."


def _build_capex_cycle(company: str, yearly_payloads: list[dict[str, object]]) -> str:
    capex_ratio_values = [_metric_value(payload, "capex_ratio") for payload in yearly_payloads]
    direction = _trajectory_direction(capex_ratio_values)
    latest_value = capex_ratio_values[-1]
    valid_values = [value for value in capex_ratio_values if isinstance(value, (int, float))]

    if direction == "up" and isinstance(latest_value, (int, float)) and latest_value > 0.15:
        return f"{company} is in an elevated capex cycle, with infrastructure intensity rising into the latest filing."
    if (
        len(valid_values) >= 3
        and valid_values[1] > valid_values[0]
        and valid_values[-1] < valid_values[1]
    ):
        return f"{company} is moderating its capex cycle relative to revenue."
    if direction == "down":
        return f"{company} is moderating its capex cycle relative to revenue."
    return f"{company} shows a stable-to-mixed capex cycle across the selected filings."


def build_multi_year_trajectory(
    company: str,
    filing_type: str,
    yearly_payloads: list[dict[str, object]],
) -> dict[str, object]:
    if len(yearly_payloads) < 2:
        raise ValueError("Trajectory analysis requires at least two filings.")

    ordered_payloads = sorted(
        yearly_payloads,
        key=lambda payload: str(payload.get("filing_date", "")),
    )
    filing_years = [str(payload.get("filing_date", ""))[:4] for payload in ordered_payloads]

    metrics: dict[str, list[dict[str, object]]] = {}
    for metric_name in TRAJECTORY_METRICS:
        metrics[metric_name] = [
            {
                "filing_date": payload.get("filing_date"),
                "value": _metric_value(payload, metric_name),
            }
            for payload in ordered_payloads
        ]

    insights = {
        "revenue_trajectory": _build_revenue_trajectory(company, ordered_payloads),
        "margin_expansion": _build_margin_expansion(company, ordered_payloads),
        "capex_cycle": _build_capex_cycle(company, ordered_payloads),
    }

    return {
        "company": company,
        "filing_type": filing_type,
        "filing_years": filing_years,
        "filing_dates": [payload.get("filing_date") for payload in ordered_payloads],
        "metrics": metrics,
        "insights": insights,
    }


def export_multi_year_trajectory_markdown(
    trajectory_payload: dict[str, object],
    output_dir: Path = TRAJECTORIES_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    company = str(trajectory_payload.get("company", "unknown"))
    filing_years = trajectory_payload.get("filing_years", [])
    year_count = len(filing_years) if isinstance(filing_years, list) else 0
    output_path = output_dir / f"{company}_{year_count}yr_analysis.md"

    metrics = trajectory_payload.get("metrics", {})
    insights = trajectory_payload.get("insights", {})
    filing_dates = trajectory_payload.get("filing_dates", [])

    lines = [
        "# Multi-Year Financial Trajectory",
        f"{company} ({trajectory_payload.get('filing_type', 'unknown')})",
        "",
        "## Filing Scope",
    ]
    for filing_date in filing_dates if isinstance(filing_dates, list) else []:
        lines.append(f"- {filing_date}")

    for metric_name in TRAJECTORY_METRICS:
        series = metrics.get(metric_name, []) if isinstance(metrics, dict) else []
        lines.extend(["", f"## {TRAJECTORY_TITLES[metric_name]} Trajectory"])
        for point in series:
            if not isinstance(point, dict):
                continue
            lines.append(
                f"- {point.get('filing_date')}: {_format_metric(metric_name, point.get('value') if isinstance(point.get('value'), (int, float)) else None)}"
            )

    lines.extend(
        [
            "",
            "## Revenue Trajectory",
            f"- {insights.get('revenue_trajectory') if isinstance(insights, dict) else 'None'}",
            "",
            "## Margin Expansion",
            f"- {insights.get('margin_expansion') if isinstance(insights, dict) else 'None'}",
            "",
            "## Capex Cycle",
            f"- {insights.get('capex_cycle') if isinstance(insights, dict) else 'None'}",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
