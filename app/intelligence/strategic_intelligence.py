from __future__ import annotations

from pathlib import Path

from app.quality import build_data_quality_notes


REPORTS_OUTPUT_DIR = Path("data") / "reports"


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


def _leader(rankings: dict[str, object], metric_name: str) -> str | None:
    ranking_payload = rankings.get(metric_name, {})
    if not isinstance(ranking_payload, dict):
        return None
    leader = ranking_payload.get("leader")
    return leader if isinstance(leader, str) else None


def _industry_structure_observations(comparison_payload: dict[str, object]) -> list[str]:
    rankings = comparison_payload.get("rankings", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    if not isinstance(rankings, dict) or not isinstance(ai_landscape, dict):
        return ["Industry structure is not fully observable from the current dataset."]

    revenue_leader = _leader(rankings, "revenue")
    platform_leaders = ai_landscape.get("ai_platform_scale_leaders", [])
    builders = ai_landscape.get("infrastructure_builders", [])

    observations: list[str] = []
    if isinstance(revenue_leader, str):
        observations.append(
            f"{revenue_leader} remains the largest revenue base in the selected peer set."
        )
    if isinstance(platform_leaders, list) and len(platform_leaders) >= 2:
        observations.append(
            f"{', '.join(platform_leaders)} combine large-scale revenue bases with platform investment capacity, reinforcing their role as AI platform leaders."
        )
    if isinstance(builders, list) and builders:
        observations.append(
            f"AI infrastructure investment is concentrated in {', '.join(builders)}, suggesting hyperscalers are expanding capacity."
        )

    return observations or ["Industry structure remains mixed across the selected companies."]


def _investment_cycle_observations(comparison_payload: dict[str, object]) -> list[str]:
    rankings = comparison_payload.get("rankings", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    if not isinstance(rankings, dict) or not isinstance(ai_landscape, dict):
        return ["The current filing set does not support a clean investment-cycle readout."]

    capex_leader = _leader(rankings, "capex_ratio")
    builders = ai_landscape.get("infrastructure_builders", [])
    scale_leaders = ai_landscape.get("ai_platform_scale_leaders", [])

    observations: list[str] = []
    if isinstance(capex_leader, str):
        observations.append(
            f"{capex_leader} leads the current capex intensity ranking, indicating the most aggressive infrastructure build cycle."
        )
    if isinstance(builders, list) and len(builders) >= 2:
        observations.append(
            f"Capacity expansion is concentrated in {', '.join(builders)}, pointing to an active hyperscaler investment phase."
        )
    if isinstance(scale_leaders, list) and scale_leaders:
        observations.append(
            f"Platform-scale deployment is led by {', '.join(scale_leaders)}, showing where AI infrastructure spending is being operationalized."
        )

    return observations or ["Investment signals remain distributed rather than concentrated."]


def _profit_pool_observations(comparison_payload: dict[str, object]) -> list[str]:
    rankings = comparison_payload.get("rankings", {})
    if not isinstance(rankings, dict):
        return ["Profit-pool dynamics are not fully observable from the current dataset."]

    operating_margin_leader = _leader(rankings, "operating_margin")
    net_income_growth_leader = _leader(rankings, "net_income_growth")
    revenue_growth_leader = _leader(rankings, "revenue_growth")
    revenue_leader = _leader(rankings, "revenue")

    observations: list[str] = []
    if isinstance(operating_margin_leader, str) and isinstance(revenue_growth_leader, str):
        if operating_margin_leader == revenue_growth_leader:
            observations.append(
                f"{operating_margin_leader} captures both the highest profitability and the strongest revenue growth layer of the AI stack."
            )
        else:
            observations.append(
                f"{operating_margin_leader} leads profitability while {revenue_growth_leader} leads top-line growth, implying a split profit pool across the stack."
            )
    if (
        isinstance(operating_margin_leader, str)
        and isinstance(net_income_growth_leader, str)
        and operating_margin_leader == net_income_growth_leader
    ):
        observations.append(
            f"{operating_margin_leader} combines margin leadership with the strongest earnings momentum, indicating strong operating leverage."
        )
    if isinstance(revenue_leader, str) and revenue_leader not in {operating_margin_leader, revenue_growth_leader}:
        observations.append(
            f"{revenue_leader} remains the largest revenue base, but current profitability and growth signals are weaker than the leading peers."
        )

    return observations or ["Profit-pool leadership remains distributed across the selected companies."]


def _positioning_observations(comparison_payload: dict[str, object]) -> list[str]:
    rankings = comparison_payload.get("rankings", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    if not isinstance(rankings, dict) or not isinstance(ai_landscape, dict):
        return ["Platform versus hardware positioning is not fully observable from the current dataset."]

    hardware = ai_landscape.get("ai_hardware_platforms", [])
    platform_leaders = ai_landscape.get("ai_platform_scale_leaders", [])
    operating_margin_leader = _leader(rankings, "operating_margin")
    revenue_growth_leader = _leader(rankings, "revenue_growth")

    observations: list[str] = []
    if (
        isinstance(hardware, list)
        and len(hardware) == 1
        and isinstance(operating_margin_leader, str)
        and isinstance(revenue_growth_leader, str)
        and hardware[0] == operating_margin_leader == revenue_growth_leader
    ):
        observations.append(
            f"{hardware[0]} captures the highest profitability and growth layer of the AI stack, indicating strong hardware leverage."
        )
    elif isinstance(hardware, list) and hardware:
        observations.append(
            f"Hardware-side AI economics are concentrated in {', '.join(hardware)}."
        )

    if isinstance(platform_leaders, list) and len(platform_leaders) >= 2:
        observations.append(
            f"{', '.join(platform_leaders)} continue to define the platform layer through scale and deployment capacity."
        )

    return observations or ["Platform and hardware leadership remain mixed across the selected companies."]


def _strategic_intelligence_observations(comparison_payload: dict[str, object]) -> list[str]:
    sections = [
        *_industry_structure_observations(comparison_payload),
        *_investment_cycle_observations(comparison_payload),
        *_profit_pool_observations(comparison_payload),
        *_positioning_observations(comparison_payload),
    ]

    observations: list[str] = []
    for section in sections:
        if section not in observations:
            observations.append(section)

    return observations[:6]


def _final_takeaways(comparison_payload: dict[str, object]) -> list[str]:
    rankings = comparison_payload.get("rankings", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    if not isinstance(rankings, dict) or not isinstance(ai_landscape, dict):
        return ["The current comparison set supports only a partial strategic readout."]

    takeaways: list[str] = []
    builders = ai_landscape.get("infrastructure_builders", [])
    hardware = ai_landscape.get("ai_hardware_platforms", [])
    platforms = ai_landscape.get("ai_platform_scale_leaders", [])
    revenue_leader = _leader(rankings, "revenue")
    operating_margin_leader = _leader(rankings, "operating_margin")
    revenue_growth_leader = _leader(rankings, "revenue_growth")

    if isinstance(builders, list) and builders:
        takeaways.append(
            f"Capacity expansion is currently centered on {', '.join(builders)}."
        )
    if (
        isinstance(hardware, list)
        and len(hardware) == 1
        and hardware[0] == operating_margin_leader == revenue_growth_leader
    ):
        takeaways.append(
            f"{hardware[0]} remains the clearest hardware profit-pool beneficiary in the current filing set."
        )
    if isinstance(platforms, list) and platforms:
        takeaways.append(
            f"The platform layer is anchored by {', '.join(platforms)}."
        )
    if isinstance(revenue_leader, str):
        takeaways.append(
            f"{revenue_leader} still provides the largest scale base across the selected peers."
        )

    return takeaways[:4] or ["The current comparison set supports only a partial strategic readout."]


def export_strategic_intelligence_report_markdown(
    comparison_payload: dict[str, object],
    output_dir: Path = REPORTS_OUTPUT_DIR,
    report_label: str = "AI_strategic_intelligence",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filing_year = str(comparison_payload.get("filing_year", "unknown"))
    output_path = output_dir / f"{report_label}_{filing_year}.md"

    companies = comparison_payload.get("companies", [])
    filing_type = str(comparison_payload.get("filing_type", "unknown"))
    filing_dates = comparison_payload.get("filing_dates", {})
    quality = comparison_payload.get("quality", {})

    lines = [
        "# AI Strategic Intelligence Report",
        "",
        "## Filing Scope",
        f"- Companies: {', '.join(companies) if isinstance(companies, list) and companies else 'Not available'}",
        f"- Filing type: {filing_type}",
        f"- Filing year: {filing_year}",
    ]

    if isinstance(filing_dates, dict):
        for company in companies if isinstance(companies, list) else []:
            lines.append(f"- {company}: {filing_dates.get(company, 'unknown')}")

    lines.extend(["", "## Data Quality Notes"])
    if isinstance(quality, dict):
        for note in build_data_quality_notes(quality):
            lines.append(f"- {note}")
    else:
        lines.append("- Quality metadata is not available for the current comparison set.")

    section_map = {
        "## Industry Structure": _industry_structure_observations(comparison_payload),
        "## Investment Cycle": _investment_cycle_observations(comparison_payload),
        "## Profit Pool Dynamics": _profit_pool_observations(comparison_payload),
        "## Platform vs Hardware Positioning": _positioning_observations(comparison_payload),
        "## Strategic Intelligence": _strategic_intelligence_observations(comparison_payload),
        "## Final Strategic Takeaways": _final_takeaways(comparison_payload),
    }

    for heading, observations in section_map.items():
        lines.extend(["", heading])
        for observation in observations:
            lines.append(f"- {observation}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
