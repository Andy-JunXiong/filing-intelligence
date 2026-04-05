from __future__ import annotations

import json
from pathlib import Path


VISUALIZATIONS_OUTPUT_DIR = Path("data") / "visualizations"
DATASET_DEFINITIONS = {
    "profit_pool_scatter": {
        "title": "Profit Pool Map",
        "x_metric": "revenue",
        "y_metric": "operating_margin",
    },
    "growth_vs_profit": {
        "title": "Growth vs Profit",
        "x_metric": "revenue_growth",
        "y_metric": "operating_margin",
    },
    "capex_vs_scale": {
        "title": "Infrastructure Investment Map",
        "x_metric": "revenue",
        "y_metric": "capex_ratio",
    },
}
POINT_METRICS = (
    "revenue",
    "operating_margin",
    "net_margin",
    "capex_ratio",
    "revenue_growth",
    "operating_income_growth",
    "net_income_growth",
)


def _metric_values_by_company(
    comparison_payload: dict[str, object],
    metric_name: str,
) -> dict[str, int | float | None]:
    rankings = comparison_payload.get("rankings", {})
    if not isinstance(rankings, dict):
        return {}

    ranking_payload = rankings.get(metric_name, {})
    if not isinstance(ranking_payload, dict):
        return {}

    ranking_entries = ranking_payload.get("ranking", [])
    if not isinstance(ranking_entries, list):
        return {}

    values: dict[str, int | float | None] = {}
    for entry in ranking_entries:
        if not isinstance(entry, dict):
            continue
        company = entry.get("company")
        value = entry.get("value")
        if isinstance(company, str):
            values[company] = value if isinstance(value, (int, float)) else None
    return values


def _insight_texts_by_company(comparison_payload: dict[str, object]) -> dict[str, list[str]]:
    insights = comparison_payload.get("insights", {})
    if not isinstance(insights, dict):
        return {}

    insight_texts: dict[str, list[str]] = {}
    for company, items in insights.items():
        if not isinstance(company, str) or not isinstance(items, list):
            continue
        texts: list[str] = []
        for item in items:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    texts.append(text)
        insight_texts[company] = texts
    return insight_texts


def _build_dataset(
    comparison_payload: dict[str, object],
    *,
    dataset_name: str,
    x_metric: str,
    y_metric: str,
    title: str,
) -> dict[str, object]:
    companies = comparison_payload.get("companies", [])
    x_values = _metric_values_by_company(comparison_payload, x_metric)
    y_values = _metric_values_by_company(comparison_payload, y_metric)
    revenue_values = _metric_values_by_company(comparison_payload, "revenue")
    signals = comparison_payload.get("signals", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    quality = comparison_payload.get("quality", {})
    evidence = comparison_payload.get("evidence", {})
    insights = _insight_texts_by_company(comparison_payload)
    metric_values_by_company = {
        metric_name: _metric_values_by_company(comparison_payload, metric_name)
        for metric_name in POINT_METRICS
    }

    infrastructure_builders = set(ai_landscape.get("infrastructure_builders", [])) if isinstance(ai_landscape, dict) else set()
    hardware_platforms = set(ai_landscape.get("ai_hardware_platforms", [])) if isinstance(ai_landscape, dict) else set()
    platform_scale_leaders = set(ai_landscape.get("ai_platform_scale_leaders", [])) if isinstance(ai_landscape, dict) else set()

    points: list[dict[str, object]] = []
    for company in companies if isinstance(companies, list) else []:
        if not isinstance(company, str):
            continue
        points.append(
            {
                "company": company,
                "x": x_values.get(company),
                "y": y_values.get(company),
                "revenue": revenue_values.get(company),
                "metrics": {
                    metric_name: metric_values_by_company[metric_name].get(company)
                    for metric_name in POINT_METRICS
                },
                "signals": signals.get(company, []) if isinstance(signals, dict) else [],
                "quality": quality.get(company, {}) if isinstance(quality, dict) else {},
                "evidence": evidence.get(company, {}) if isinstance(evidence, dict) else {},
                "takeaways": insights.get(company, []),
                "roles": {
                    "infrastructure_builder": company in infrastructure_builders,
                    "ai_hardware_platform": company in hardware_platforms,
                    "ai_platform_scale": company in platform_scale_leaders,
                },
                "comparable": isinstance(x_values.get(company), (int, float))
                and isinstance(y_values.get(company), (int, float)),
            }
        )

    comparable_points = [
        point for point in points if isinstance(point.get("x"), (int, float)) and isinstance(point.get("y"), (int, float))
    ]
    return {
        "dataset": dataset_name,
        "title": title,
        "filing_type": comparison_payload.get("filing_type"),
        "filing_year": comparison_payload.get("filing_year"),
        "x_metric": x_metric,
        "y_metric": y_metric,
        "point_count": len(comparable_points),
        "points": points,
    }


def build_visualization_datasets(
    comparison_payload: dict[str, object],
) -> dict[str, dict[str, object]]:
    return {
        dataset_name: _build_dataset(
            comparison_payload,
            dataset_name=dataset_name,
            x_metric=config["x_metric"],
            y_metric=config["y_metric"],
            title=config["title"],
        )
        for dataset_name, config in DATASET_DEFINITIONS.items()
    }


def export_visualization_datasets(
    comparison_payload: dict[str, object],
    output_dir: Path = VISUALIZATIONS_OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets = build_visualization_datasets(comparison_payload)

    output_paths: dict[str, Path] = {}
    for dataset_name, dataset_payload in datasets.items():
        output_path = output_dir / f"{dataset_name}.json"
        output_path.write_text(
            json.dumps(dataset_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        output_paths[dataset_name] = output_path

    return output_paths


def export_visual_intelligence_markdown(
    comparison_payload: dict[str, object],
    output_dir: Path = VISUALIZATIONS_OUTPUT_DIR,
    report_label: str = "AI_visual_intelligence",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filing_year = str(comparison_payload.get("filing_year", "unknown"))
    output_path = output_dir / f"{report_label}_{filing_year}.md"

    datasets = build_visualization_datasets(comparison_payload)
    rankings = comparison_payload.get("rankings", {})
    ai_landscape = comparison_payload.get("ai_infrastructure_landscape", {})
    companies = comparison_payload.get("companies", [])

    revenue_leader = rankings.get("revenue", {}).get("leader") if isinstance(rankings, dict) and isinstance(rankings.get("revenue"), dict) else None
    operating_margin_leader = rankings.get("operating_margin", {}).get("leader") if isinstance(rankings, dict) and isinstance(rankings.get("operating_margin"), dict) else None
    revenue_growth_leader = rankings.get("revenue_growth", {}).get("leader") if isinstance(rankings, dict) and isinstance(rankings.get("revenue_growth"), dict) else None
    capex_ratio_leader = rankings.get("capex_ratio", {}).get("leader") if isinstance(rankings, dict) and isinstance(rankings.get("capex_ratio"), dict) else None

    builders = ai_landscape.get("infrastructure_builders", []) if isinstance(ai_landscape, dict) else []
    hardware = ai_landscape.get("ai_hardware_platforms", []) if isinstance(ai_landscape, dict) else []
    platforms = ai_landscape.get("ai_platform_scale_leaders", []) if isinstance(ai_landscape, dict) else []

    lines = [
        "# AI Visual Intelligence",
        "",
        f"- Companies: {', '.join(companies) if isinstance(companies, list) else 'Not available'}",
        f"- Filing type: {comparison_payload.get('filing_type', 'unknown')}",
        f"- Filing year: {filing_year}",
        "",
        "## Profit Pool Map",
        f"- Dataset: profit_pool_scatter.json ({datasets['profit_pool_scatter']['point_count']} comparable points)",
        f"- Revenue leader: {revenue_leader or 'Not available'}",
        f"- Operating margin leader: {operating_margin_leader or 'Not available'}",
        "",
        "## Growth vs Profit",
        f"- Dataset: growth_vs_profit.json ({datasets['growth_vs_profit']['point_count']} comparable points)",
        f"- Growth leader: {revenue_growth_leader or 'Not available'}",
        f"- Profitability leader: {operating_margin_leader or 'Not available'}",
        "",
        "## Infrastructure Investment Map",
        f"- Dataset: capex_vs_scale.json ({datasets['capex_vs_scale']['point_count']} comparable points)",
        f"- Capex intensity leader: {capex_ratio_leader or 'Not available'}",
        f"- Infrastructure builders: {', '.join(builders) if builders else 'None identified'}",
        "",
        "## AI Ecosystem Structure",
        f"- AI hardware platforms: {', '.join(hardware) if hardware else 'None identified'}",
        f"- AI platform scale leaders: {', '.join(platforms) if platforms else 'None identified'}",
        f"- Infrastructure builders: {', '.join(builders) if builders else 'None identified'}",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
