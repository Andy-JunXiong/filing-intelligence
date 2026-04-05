from __future__ import annotations

import json
from pathlib import Path

from app.quality import assess_extracted_payload_quality
from app.schemas import CompanyInsight, ExtractedMetric, FilingMetadata, PipelineStageResult


EXTRACTED_OUTPUT_DIR = Path("data") / "extracted"


def export_insight(company_insight: CompanyInsight) -> PipelineStageResult:
    """Return placeholder export metadata for the output stage."""
    return PipelineStageResult(
        stage="export",
        payload={
            "company": company_insight.company,
            "format": "json",
            "status": "placeholder-exported",
        },
    )


def build_extracted_metrics_payload(
    metadata: FilingMetadata,
    metrics: dict[str, ExtractedMetric | None],
) -> dict[str, object]:
    financial_metrics = {
        metric_name: metric.to_dict() if metric is not None else None
        for metric_name, metric in metrics.items()
    }
    payload = {
        "ticker": metadata.ticker,
        "filing_type": metadata.filing_type,
        "filing_date": metadata.filing_date,
        "company": metadata.company,
        "source_url": metadata.source_url,
        "financial_metrics": financial_metrics,
    }
    payload["quality"] = assess_extracted_payload_quality(payload, company=metadata.ticker)
    return payload


def export_extracted_metrics(
    metadata: FilingMetadata,
    metrics: dict[str, ExtractedMetric | None],
    output_dir: Path = EXTRACTED_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{metadata.ticker}_{metadata.filing_type}_{metadata.filing_date}.json"
    payload = build_extracted_metrics_payload(metadata, metrics)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
