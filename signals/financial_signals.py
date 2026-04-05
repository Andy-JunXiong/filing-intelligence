from __future__ import annotations

import json
import logging
from pathlib import Path

from app.quality import assess_signals_quality


SIGNALS_OUTPUT_DIR = Path("data") / "signals"
logger = logging.getLogger(__name__)
AI_INFRASTRUCTURE_BUILDER = "AI Infrastructure Builder"
AI_HARDWARE_PLATFORM = "AI Hardware Platform"
AI_PLATFORM_SCALE = "AI Platform Scale"


def _safe_ratio(numerator: int | float | None, denominator: int | float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _metric_value(extracted_payload: dict[str, object], metric_name: str) -> int | float | None:
    financial_metrics = extracted_payload.get("financial_metrics", {})
    if not isinstance(financial_metrics, dict):
        return None
    metric = financial_metrics.get(metric_name)
    if not isinstance(metric, dict):
        return None
    value = metric.get("numeric_value")
    if isinstance(value, (int, float)):
        return value
    return None


def _validated_ratio(
    metric_name: str,
    value: float | None,
    *,
    company: str,
    filing_date: object,
    warnings: list[str],
) -> float | None:
    if value is None:
        return None

    if metric_name in {"operating_margin", "net_margin"} and -1 <= value <= 1:
        return value
    if metric_name == "capex_ratio" and 0 <= value <= 1:
        return value

    logger.warning(
        "Discarding implausible %s for %s (%s): %.3f",
        metric_name,
        company,
        filing_date,
        value,
    )
    warnings.append(
        f"{metric_name}={value:.3f} is outside the expected range for {company} ({filing_date})."
    )
    return None


def _validated_growth(
    metric_name: str,
    value: float | None,
    *,
    company: str,
    filing_date: object,
    warnings: list[str],
) -> float | None:
    if value is None:
        return None

    if -1 <= value <= 10:
        return value

    logger.warning(
        "Discarding implausible %s for %s (%s): %.3f",
        metric_name,
        company,
        filing_date,
        value,
    )
    warnings.append(
        f"{metric_name}={value:.3f} exceeds the reasonable growth bound for {company} ({filing_date})."
    )
    return None


def build_financial_signals(extracted_payload: dict[str, object]) -> dict[str, object]:
    company = str(extracted_payload.get("ticker") or extracted_payload.get("company") or "unknown")
    filing_date = extracted_payload.get("filing_date")
    warnings: list[str] = []
    revenue = _metric_value(extracted_payload, "revenue")
    previous_revenue = _metric_value(extracted_payload, "previous_revenue")
    operating_income = _metric_value(extracted_payload, "operating_income")
    previous_operating_income = _metric_value(extracted_payload, "previous_operating_income")
    net_income = _metric_value(extracted_payload, "net_income")
    previous_net_income = _metric_value(extracted_payload, "previous_net_income")
    capex = _metric_value(extracted_payload, "capex")

    operating_margin = _validated_ratio(
        "operating_margin",
        _safe_ratio(operating_income, revenue),
        company=company,
        filing_date=filing_date,
        warnings=warnings,
    )
    net_margin = _validated_ratio(
        "net_margin",
        _safe_ratio(net_income, revenue),
        company=company,
        filing_date=filing_date,
        warnings=warnings,
    )
    capex_ratio = _validated_ratio(
        "capex_ratio",
        _safe_ratio(abs(capex) if capex is not None else None, revenue),
        company=company,
        filing_date=filing_date,
        warnings=warnings,
    )
    revenue_growth = _validated_growth(
        "revenue_growth",
        _safe_ratio(
            revenue - previous_revenue if revenue is not None and previous_revenue is not None else None,
            previous_revenue,
        ),
        company=company,
        filing_date=filing_date,
        warnings=warnings,
    )
    operating_income_growth = _validated_growth(
        "operating_income_growth",
        _safe_ratio(
            operating_income - previous_operating_income
            if operating_income is not None and previous_operating_income is not None
            else None,
            previous_operating_income,
        ),
        company=company,
        filing_date=filing_date,
        warnings=warnings,
    )
    net_income_growth = _validated_growth(
        "net_income_growth",
        _safe_ratio(
            net_income - previous_net_income
            if net_income is not None and previous_net_income is not None
            else None,
            previous_net_income,
        ),
        company=company,
        filing_date=filing_date,
        warnings=warnings,
    )

    metrics_payload = {
        "operating_margin": round(operating_margin, 3) if operating_margin is not None else None,
        "net_margin": round(net_margin, 3) if net_margin is not None else None,
        "capex_ratio": round(capex_ratio, 3) if capex_ratio is not None else None,
        "revenue_growth": round(revenue_growth, 3) if revenue_growth is not None else None,
        "operating_income_growth": round(operating_income_growth, 3) if operating_income_growth is not None else None,
        "net_income_growth": round(net_income_growth, 3) if net_income_growth is not None else None,
    }

    signals: list[dict[str, object]] = []
    if capex_ratio is not None and capex_ratio > 0.20:
        signals.append(
            {
                "type": "capex_intensity",
                "value": round(capex_ratio, 3),
                "signal": "High infrastructure investment",
            }
        )
    if operating_margin is not None and operating_margin > 0.35:
        signals.append(
            {
                "type": "operating_margin",
                "value": round(operating_margin, 3),
                "signal": "High profitability",
            }
        )
    if capex_ratio is not None and capex_ratio > 0.15 and revenue is not None and revenue > 100000:
        signals.append(
            {
                "type": "ai_infrastructure_builder",
                "value": round(capex_ratio, 3),
                "signal": AI_INFRASTRUCTURE_BUILDER,
            }
        )
    if (
        operating_margin is not None
        and operating_margin > 0.50
        and capex_ratio is not None
        and capex_ratio < 0.10
    ):
        signals.append(
            {
                "type": "ai_hardware_platform",
                "value": round(operating_margin, 3),
                "signal": AI_HARDWARE_PLATFORM,
            }
        )
    if capex_ratio is not None and capex_ratio > 0.10 and revenue is not None and revenue > 200000:
        signals.append(
            {
                "type": "ai_platform_scale",
                "value": round(capex_ratio, 3),
                "signal": AI_PLATFORM_SCALE,
            }
        )

    return {
        "company": company,
        "filing_type": extracted_payload.get("filing_type"),
        "filing_date": filing_date,
        "metrics": metrics_payload,
        "signals": signals,
        "warnings": warnings,
        "quality": assess_signals_quality(
            company=company,
            warnings=warnings,
            metrics=metrics_payload,
            extracted_payload=extracted_payload,
        ),
    }


def export_financial_signals(
    signals_payload: dict[str, object],
    output_dir: Path = SIGNALS_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    company = str(signals_payload.get("company", "unknown"))
    filing_type = str(signals_payload.get("filing_type", "unknown"))
    filing_date = str(signals_payload.get("filing_date", "unknown"))
    filing_year = filing_date[:4] if len(filing_date) >= 4 else filing_date
    output_path = output_dir / f"{company}_{filing_type}_{filing_year}.json"
    output_path.write_text(json.dumps(signals_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
