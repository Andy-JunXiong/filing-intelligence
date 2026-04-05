from __future__ import annotations

from pathlib import Path


INSIGHTS_OUTPUT_DIR = Path("data") / "insights"


def build_structured_insight(
    extracted_payload: dict[str, object],
    financial_signals_payload: dict[str, object],
) -> dict[str, object]:
    metrics_summary = financial_signals_payload.get("metrics", {})
    signals = financial_signals_payload.get("signals", [])

    operating_margin = None
    capex_ratio = None
    if isinstance(metrics_summary, dict):
        operating_margin = metrics_summary.get("operating_margin")
        capex_ratio = metrics_summary.get("capex_ratio")

    takeaways: list[dict[str, object]] = []
    if capex_ratio is not None and capex_ratio > 0.20 and operating_margin is not None and operating_margin > 0.35:
        takeaways.append(
            {
                "text": "The company combines strong profitability with elevated infrastructure investment, suggesting capacity to fund long-term AI expansion.",
                "evidence": {
                    "operating_margin": operating_margin,
                    "capex_ratio": capex_ratio,
                    "signals": ["High infrastructure investment", "High profitability"],
                },
            }
        )
    if capex_ratio is not None and capex_ratio > 0.20:
        takeaways.append(
            {
                "text": "The company is investing heavily in infrastructure relative to revenue.",
                "evidence": {
                    "capex_ratio": capex_ratio,
                    "signal": "High infrastructure investment",
                },
            }
        )
    if operating_margin is not None and operating_margin > 0.35:
        takeaways.append(
            {
                "text": "The company maintains strong operating profitability.",
                "evidence": {
                    "operating_margin": operating_margin,
                    "signal": "High profitability",
                },
            }
        )

    return {
        "company": extracted_payload.get("ticker") or extracted_payload.get("company"),
        "filing_type": extracted_payload.get("filing_type"),
        "filing_date": extracted_payload.get("filing_date"),
        "metrics_summary": metrics_summary,
        "signals_summary": [signal.get("signal") for signal in signals if isinstance(signal, dict)],
        "takeaways": takeaways[:3],
    }


def export_structured_insight(
    insight_payload: dict[str, object],
    output_dir: Path = INSIGHTS_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    company = str(insight_payload.get("company", "unknown"))
    filing_type = str(insight_payload.get("filing_type", "unknown"))
    filing_date = str(insight_payload.get("filing_date", "unknown"))
    filing_year = filing_date[:4] if len(filing_date) >= 4 else filing_date
    output_path = output_dir / f"{company}_{filing_type}_{filing_year}.md"

    metrics_summary = insight_payload.get("metrics_summary", {})
    signals_summary = insight_payload.get("signals_summary", [])
    takeaways = insight_payload.get("takeaways", [])

    lines = [
        f"# Insight v1: {company} {filing_type} ({filing_date})",
        "",
        "## Metrics Summary",
    ]
    if isinstance(metrics_summary, dict):
        for key, value in metrics_summary.items():
            lines.append(f"- {key}: {value}")

    lines.extend(["", "## Signals Summary"])
    if isinstance(signals_summary, list) and signals_summary:
        for signal in signals_summary:
            lines.append(f"- {signal}")
    else:
        lines.append("- None")

    lines.extend(["", "## Takeaways"])
    if isinstance(takeaways, list) and takeaways:
        for takeaway in takeaways:
            if isinstance(takeaway, dict):
                lines.append(f"- {takeaway.get('text')}")
                evidence = takeaway.get("evidence", {})
                if isinstance(evidence, dict) and evidence:
                    evidence_parts = [f"{key}={value}" for key, value in evidence.items()]
                    lines.append(f"  Evidence: {', '.join(evidence_parts)}")
            else:
                lines.append(f"- {takeaway}")
    else:
        lines.append("- None")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
