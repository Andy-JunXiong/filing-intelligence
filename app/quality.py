from __future__ import annotations


CORE_CURRENT_METRICS = ("revenue", "operating_income", "net_income", "capex")
CORE_PRIOR_METRICS = (
    "previous_revenue",
    "previous_operating_income",
    "previous_net_income",
)
CORE_METRICS = CORE_CURRENT_METRICS + CORE_PRIOR_METRICS
GENERIC_FALLBACK_KEYWORDS = {"revenue", "revenues"}


def _metric_dict(payload: dict[str, object], metric_name: str) -> dict[str, object] | None:
    financial_metrics = payload.get("financial_metrics", {})
    if not isinstance(financial_metrics, dict):
        return None
    metric = financial_metrics.get(metric_name)
    return metric if isinstance(metric, dict) else None


def _metric_numeric_value(metric: dict[str, object] | None) -> int | float | None:
    if not isinstance(metric, dict):
        return None
    value = metric.get("numeric_value")
    return value if isinstance(value, (int, float)) else None


def _metric_has_full_evidence(metric: dict[str, object] | None) -> bool:
    if not isinstance(metric, dict):
        return False
    for field_name in ("source_keyword", "source_snippet", "section", "raw_match", "unit"):
        value = metric.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return False
    return True


def assess_extracted_payload_quality(
    extracted_payload: dict[str, object],
    *,
    company: str | None = None,
) -> dict[str, object]:
    company_label = company or str(extracted_payload.get("ticker") or extracted_payload.get("company") or "unknown")
    missing_current_metrics: list[str] = []
    missing_prior_metrics: list[str] = []
    fallback_metrics: list[str] = []
    incomplete_evidence_metrics: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, dict[str, object]] = {}

    for metric_name in CORE_METRICS:
        metric = _metric_dict(extracted_payload, metric_name)
        numeric_value = _metric_numeric_value(metric)
        if metric_name in CORE_CURRENT_METRICS and numeric_value is None:
            missing_current_metrics.append(metric_name)
        if metric_name in CORE_PRIOR_METRICS and numeric_value is None:
            missing_prior_metrics.append(metric_name)

        metric_keyword = metric.get("source_keyword") if isinstance(metric, dict) else None
        if isinstance(metric_keyword, str) and metric_keyword.lower() in GENERIC_FALLBACK_KEYWORDS:
            fallback_metrics.append(metric_name)
        if numeric_value is not None and not _metric_has_full_evidence(metric):
            incomplete_evidence_metrics.append(metric_name)

        evidence[metric_name] = {
            "present": numeric_value is not None,
            "has_full_evidence": _metric_has_full_evidence(metric),
        }

    revenue_value = _metric_numeric_value(_metric_dict(extracted_payload, "revenue"))
    if revenue_value is None or revenue_value <= 0:
        warnings.append(f"{company_label} revenue must be greater than zero.")

    confidence = "high"
    if warnings or len(missing_current_metrics) >= 2:
        confidence = "low"
    elif missing_current_metrics or missing_prior_metrics or fallback_metrics or incomplete_evidence_metrics:
        confidence = "medium"

    return {
        "confidence": confidence,
        "warnings": warnings,
        "missing_current_metrics": missing_current_metrics,
        "missing_prior_metrics": missing_prior_metrics,
        "fallback_metrics": fallback_metrics,
        "incomplete_evidence_metrics": incomplete_evidence_metrics,
        "evidence": evidence,
    }


def assess_signals_quality(
    *,
    company: str,
    warnings: list[str],
    metrics: dict[str, object],
    extracted_payload: dict[str, object],
) -> dict[str, object]:
    notes: list[str] = []
    missing_growth_inputs = [
        metric_name
        for metric_name in CORE_PRIOR_METRICS
        if _metric_numeric_value(_metric_dict(extracted_payload, metric_name)) is None
    ]
    missing_metric_outputs = [
        metric_name
        for metric_name, value in metrics.items()
        if value is None
    ]

    if missing_growth_inputs:
        notes.append(
            f"{company} growth signals should be interpreted with caution due to missing prior-year evidence."
        )

    confidence = "high"
    if warnings:
        confidence = "low"
    elif missing_growth_inputs or missing_metric_outputs:
        confidence = "medium"

    return {
        "confidence": confidence,
        "warnings": warnings,
        "missing_growth_inputs": missing_growth_inputs,
        "missing_metric_outputs": missing_metric_outputs,
        "notes": notes,
    }


def merge_company_quality(
    company: str,
    extracted_payload: dict[str, object],
    signals_payload: dict[str, object],
) -> dict[str, object]:
    extracted_quality = extracted_payload.get("quality")
    if not isinstance(extracted_quality, dict):
        extracted_quality = assess_extracted_payload_quality(extracted_payload, company=company)

    signal_quality = signals_payload.get("quality")
    if not isinstance(signal_quality, dict):
        metrics = signals_payload.get("metrics", {})
        signal_quality = assess_signals_quality(
            company=company,
            warnings=[
                warning
                for warning in signals_payload.get("warnings", [])
                if isinstance(warning, str)
            ],
            metrics=metrics if isinstance(metrics, dict) else {},
            extracted_payload=extracted_payload,
        )

    warnings = [
        *[warning for warning in extracted_quality.get("warnings", []) if isinstance(warning, str)],
        *[warning for warning in signal_quality.get("warnings", []) if isinstance(warning, str)],
    ]
    notes = [
        *[note for note in signal_quality.get("notes", []) if isinstance(note, str)],
    ]

    fallback_metrics = [
        metric_name
        for metric_name in extracted_quality.get("fallback_metrics", [])
        if isinstance(metric_name, str)
    ]
    if fallback_metrics:
        metric_labels = ", ".join(
            sorted({metric_name.replace("previous_", "") for metric_name in fallback_metrics})
        )
        notes.append(f"{company} {metric_labels} required fallback extraction logic.")

    missing_prior_metrics = [
        metric_name
        for metric_name in extracted_quality.get("missing_prior_metrics", [])
        if isinstance(metric_name, str)
    ]
    if not warnings and not notes and extracted_quality.get("confidence") == "high" and signal_quality.get("confidence") == "high":
        notes.append(f"All core metrics were extracted with high confidence for {company}.")

    confidence_levels = {
        str(extracted_quality.get("confidence", "medium")),
        str(signal_quality.get("confidence", "medium")),
    }
    if "low" in confidence_levels or warnings:
        confidence = "low"
    elif "medium" in confidence_levels:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "confidence": confidence,
        "warnings": warnings,
        "notes": notes,
        "fallback_metrics": fallback_metrics,
        "missing_prior_metrics": missing_prior_metrics,
        "evidence": extracted_quality.get("evidence", {}),
    }


def build_data_quality_notes(
    quality_by_company: dict[str, object],
) -> list[str]:
    notes: list[str] = []
    high_confidence_companies: list[str] = []

    for company, quality in quality_by_company.items():
        if not isinstance(company, str) or not isinstance(quality, dict):
            continue
        confidence = quality.get("confidence")
        company_notes = [note for note in quality.get("notes", []) if isinstance(note, str)]
        company_warnings = [warning for warning in quality.get("warnings", []) if isinstance(warning, str)]
        if confidence == "high" and not company_warnings:
            high_confidence_companies.append(company)
        for note in company_notes:
            if note not in notes:
                notes.append(note)
        if company_warnings:
            notes.append(f"{company} validation warnings: {'; '.join(company_warnings)}")

    if high_confidence_companies:
        if len(high_confidence_companies) == 1:
            aggregate_note = f"All core metrics were extracted with high confidence for {high_confidence_companies[0]}."
        else:
            aggregate_note = (
                "All core metrics were extracted with high confidence for "
                + ", ".join(high_confidence_companies)
                + "."
            )
        notes = [note for note in notes if note != aggregate_note]
        notes.insert(0, aggregate_note)

    return notes or ["Quality metadata is not available for the current comparison set."]
