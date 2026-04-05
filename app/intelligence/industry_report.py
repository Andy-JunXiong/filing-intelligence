from __future__ import annotations

from pathlib import Path

from app.quality import build_data_quality_notes


REPORTS_OUTPUT_DIR = Path("data") / "reports"


def _format_value(metric_name: str, value: int | float | None) -> str:
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


def _top_ranked_companies(
    rankings: dict[str, object],
    metric_name: str,
    limit: int = 3,
) -> list[str]:
    ranking_payload = rankings.get(metric_name, {})
    if not isinstance(ranking_payload, dict):
        return []

    ranking_entries = ranking_payload.get("ranking", [])
    if not isinstance(ranking_entries, list):
        return []

    leaders: list[str] = []
    for entry in ranking_entries:
        if not isinstance(entry, dict):
            continue
        company = entry.get("company")
        value = entry.get("value")
        if not isinstance(company, str) or not isinstance(value, (int, float)):
            continue
        leaders.append(company)
        if len(leaders) >= limit:
            break

    return leaders


def _ranking_lines(
    rankings: dict[str, object],
    metric_name: str,
    *,
    limit: int = 3,
) -> list[str]:
    ranking_payload = rankings.get(metric_name, {})
    if not isinstance(ranking_payload, dict):
        return ["- Not available"]

    ranking_entries = ranking_payload.get("ranking", [])
    if not isinstance(ranking_entries, list):
        return ["- Not available"]

    lines: list[str] = []
    for entry in ranking_entries:
        if not isinstance(entry, dict):
            continue
        rank = entry.get("rank")
        company = entry.get("company")
        value = entry.get("value")
        if not isinstance(company, str):
            continue
        rank_label = f"{rank}." if isinstance(rank, int) else "-"
        lines.append(
            f"{rank_label} {company}: {_format_value(metric_name, value if isinstance(value, (int, float)) else None)}"
        )
        if len(lines) >= limit:
            break

    return lines or ["- Not available"]


def _strategic_observations(comparison_payload: dict[str, object]) -> list[str]:
    observations: list[str] = []
    rankings = comparison_payload.get("rankings", {})
    if not isinstance(rankings, dict):
        return observations

    revenue_leader = rankings.get("revenue", {}).get("leader") if isinstance(rankings.get("revenue"), dict) else None
    operating_margin_leader = (
        rankings.get("operating_margin", {}).get("leader")
        if isinstance(rankings.get("operating_margin"), dict)
        else None
    )
    revenue_growth_leader = (
        rankings.get("revenue_growth", {}).get("leader")
        if isinstance(rankings.get("revenue_growth"), dict)
        else None
    )
    net_income_growth_leader = (
        rankings.get("net_income_growth", {}).get("leader")
        if isinstance(rankings.get("net_income_growth"), dict)
        else None
    )

    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    if isinstance(ai_landscape, dict):
        builders = ai_landscape.get("infrastructure_builders", [])
        hardware = ai_landscape.get("ai_hardware_platforms", [])
        scale_leaders = ai_landscape.get("ai_platform_scale_leaders", [])
    else:
        builders = []
        hardware = []
        scale_leaders = []

    if isinstance(revenue_leader, str):
        observations.append(
            f"{revenue_leader} anchors the industry revenue base among the selected companies."
        )
    if isinstance(operating_margin_leader, str):
        observations.append(
            f"{operating_margin_leader} sets the profitability benchmark on operating margin."
        )
    if isinstance(revenue_growth_leader, str) and isinstance(net_income_growth_leader, str):
        if revenue_growth_leader == net_income_growth_leader:
            observations.append(
                f"{revenue_growth_leader} leads both revenue and earnings growth, indicating the strongest current momentum."
            )
        else:
            observations.append(
                f"{revenue_growth_leader} leads revenue growth while {net_income_growth_leader} leads net income growth, pointing to differentiated growth profiles."
            )
    elif isinstance(revenue_growth_leader, str):
        observations.append(
            f"{revenue_growth_leader} shows the strongest top-line growth momentum."
        )

    if isinstance(builders, list) and builders:
        observations.append(
            "Infrastructure spending remains concentrated in "
            + ", ".join(builders)
            + "."
        )
    if isinstance(hardware, list) and hardware:
        observations.append(
            "AI hardware demand is most visible in "
            + ", ".join(hardware)
            + "."
        )
    if isinstance(scale_leaders, list) and scale_leaders:
        observations.append(
            "Platform-scale AI investment is led by "
            + ", ".join(scale_leaders)
            + "."
        )

    takeaways = comparison_payload.get("takeaways", [])
    if isinstance(takeaways, list):
        for takeaway in takeaways:
            if isinstance(takeaway, str) and takeaway not in observations:
                observations.append(takeaway)

    return observations[:6]


def export_industry_intelligence_report_markdown(
    comparison_payload: dict[str, object],
    output_dir: Path = REPORTS_OUTPUT_DIR,
    report_label: str = "AI_industry_intelligence",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filing_year = str(comparison_payload.get("filing_year", "unknown"))
    output_path = output_dir / f"{report_label}_{filing_year}.md"

    companies = comparison_payload.get("companies", [])
    filing_type = str(comparison_payload.get("filing_type", "unknown"))
    filing_dates = comparison_payload.get("filing_dates", {})
    rankings = comparison_payload.get("rankings", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    observations = _strategic_observations(comparison_payload)
    quality = comparison_payload.get("quality", {})

    builders = ai_landscape.get("infrastructure_builders", []) if isinstance(ai_landscape, dict) else []
    hardware = ai_landscape.get("ai_hardware_platforms", []) if isinstance(ai_landscape, dict) else []
    scale_leaders = ai_landscape.get("ai_platform_scale_leaders", []) if isinstance(ai_landscape, dict) else []

    lines = [
        "# AI Industry Intelligence Report",
        "",
        "## Filing Scope",
        f"- Companies: {', '.join(companies) if isinstance(companies, list) and companies else 'Not available'}",
        f"- Filing type: {filing_type}",
        f"- Filing year: {filing_year}",
    ]

    if isinstance(filing_dates, dict):
        for company in companies if isinstance(companies, list) else []:
            lines.append(f"- {company}: {filing_dates.get(company, 'unknown')}")

    lines.extend(
        [
            "",
            "## Industry Scale",
            "- Top revenue platforms:",
            *_ranking_lines(rankings if isinstance(rankings, dict) else {}, "revenue"),
            "",
            "## Profitability Leaders",
            "- Operating margin ranking:",
            *_ranking_lines(rankings if isinstance(rankings, dict) else {}, "operating_margin"),
            "",
            "## Growth Leaders",
            "- Revenue growth ranking:",
            *_ranking_lines(rankings if isinstance(rankings, dict) else {}, "revenue_growth"),
            "- Net income growth ranking:",
            *_ranking_lines(rankings if isinstance(rankings, dict) else {}, "net_income_growth"),
            "",
            "## Infrastructure Builders",
            f"- Companies investing heavily in AI infrastructure: {', '.join(builders) if builders else 'None identified'}",
            f"- Capex ratio leaders: {', '.join(_top_ranked_companies(rankings if isinstance(rankings, dict) else {}, 'capex_ratio')) or 'Not available'}",
            "",
            "## AI Hardware Platforms",
            f"- Companies benefiting from AI hardware demand: {', '.join(hardware) if hardware else 'None identified'}",
            f"- Operating margin leaders: {', '.join(_top_ranked_companies(rankings if isinstance(rankings, dict) else {}, 'operating_margin')) or 'Not available'}",
            "",
            "## Data Quality Notes",
            "",
            "## Strategic Observations",
        ]
    )

    if isinstance(quality, dict):
        quality_notes = build_data_quality_notes(quality)
        lines[-2:-2] = [f"- {note}" for note in quality_notes]
    else:
        lines[-2:-2] = ["- Quality metadata is not available for the current comparison set."]

    if observations:
        for observation in observations:
            lines.append(f"- {observation}")
    else:
        lines.append("- No deterministic industry observations were generated.")

    if scale_leaders:
        lines.extend(
            [
                "",
                "## AI Platform Scale",
                f"- Platform-scale AI investment leaders: {', '.join(scale_leaders)}",
            ]
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
