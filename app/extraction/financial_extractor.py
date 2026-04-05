from __future__ import annotations

import re

from app.schemas import ExtractedMetric, ParsedFiling


FINANCIAL_FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "revenue": ("total revenues", "total revenue", "net revenues", "net revenue", "net sales", "revenues", "revenue"),
    "operating_income": ("operating income", "income from operations"),
    "net_income": ("net income",),
    "capex": (
        "additions to property and equipment",
        "purchases related to property and equipment",
        "capital expenditures",
        "purchases of property and equipment",
        "capex",
    ),
}
AMOUNT_PATTERN_TEXT = r"\(?\$?\d[\d,]*(?:\.\d+)?(?:\s*(?:million|billion|thousand))?\)?"
AMOUNT_PATTERN = re.compile(AMOUNT_PATTERN_TEXT, re.IGNORECASE)
LINE_AMOUNT_PATTERN = re.compile(AMOUNT_PATTERN_TEXT, re.IGNORECASE)
PREVIEW_LIMIT = 1000
PATTERN_ERROR = getattr(re, "PatternError", re.error)
AMOUNT_SCALE_PATTERN = re.compile(r"\b(?:million|billion|thousand)\b", re.IGNORECASE)
SECTION_LABEL = "financials"
SNIPPET_WINDOW = 220
REVENUE_EXCLUDED_PHRASES = (
    "accrued revenue",
    "deferred revenue",
    "revenue share",
    "internal revenue service",
    "remaining performance obligation",
)
GROWTH_BASE_FIELDS = ("revenue", "operating_income", "net_income")


def _looks_like_financial_amount(amount: str) -> bool:
    return (
        "," in amount
        or "." in amount
        or "$" in amount
        or "(" in amount
        or ")" in amount
        or AMOUNT_SCALE_PATTERN.search(amount) is not None
    )


def _normalize_amount(raw_value: str | None) -> tuple[int | float | None, str | None]:
    if raw_value is None:
        return None, None

    cleaned = raw_value.strip()
    if not cleaned:
        return None, None

    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()").replace("$", "").replace(",", "").strip()

    match = AMOUNT_SCALE_PATTERN.search(cleaned)
    scale = match.group(0).lower() if match is not None else None
    if scale is not None:
        cleaned = AMOUNT_SCALE_PATTERN.sub("", cleaned).strip()

    if not cleaned:
        return None, None

    numeric_value: int | float
    if "." in cleaned:
        numeric_value = float(cleaned)
    else:
        numeric_value = int(cleaned)

    if negative:
        numeric_value = -numeric_value

    if scale == "million":
        numeric_value *= 1_000_000
    elif scale == "billion":
        numeric_value *= 1_000_000_000
    elif scale == "thousand":
        numeric_value *= 1_000

    if isinstance(numeric_value, float) and numeric_value.is_integer():
        numeric_value = int(numeric_value)

    return numeric_value, scale


def _infer_unit(section_text: str) -> str | None:
    lowered = section_text.lower()
    if "in millions" in lowered:
        return "million_usd"
    if "in billions" in lowered:
        return "billion_usd"
    if "in thousands" in lowered:
        return "thousand_usd"
    return None


def _extract_amount_from_line(line: str) -> str | None:
    amounts = LINE_AMOUNT_PATTERN.findall(line)
    if not amounts:
        return None

    for amount in amounts:
        normalized_digits = re.sub(r"[^0-9]", "", amount)
        if len(normalized_digits) >= 4 and _looks_like_financial_amount(amount):
            return amount.strip()

    return amounts[0].strip()


def _extract_amounts_from_line(line: str) -> list[str]:
    amounts = LINE_AMOUNT_PATTERN.findall(line)
    extracted: list[str] = []
    for amount in amounts:
        normalized_digits = re.sub(r"[^0-9]", "", amount)
        if len(normalized_digits) < 4:
            continue
        if not _looks_like_financial_amount(amount) and int(normalized_digits) <= 2100:
            continue
        extracted.append(amount.strip())
    return extracted


def _is_excluded_revenue_line(line: str) -> bool:
    lowered = line.lower()
    return any(phrase in lowered for phrase in REVENUE_EXCLUDED_PHRASES)


def get_financials_section_preview(
    parsed_filing: ParsedFiling,
    limit: int = PREVIEW_LIMIT,
) -> str:
    """Return a short preview of the financials section for debugging."""
    financials_text = parsed_filing.sections.get(SECTION_LABEL, "").strip()
    if not financials_text:
        return ""
    return financials_text[:limit]


def _build_keyword_search_pattern(keyword: str) -> re.Pattern[str] | None:
    try:
        return re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE)
    except PATTERN_ERROR:
        return None


def _build_keyword_amount_pattern(keyword: str) -> re.Pattern[str] | None:
    try:
        return re.compile(
            rf"{re.escape(keyword)}[^.\n:]*[:\-]?\s*({AMOUNT_PATTERN_TEXT})",
            re.IGNORECASE | re.DOTALL,
        )
    except PATTERN_ERROR:
        return None


def _build_metric(
    *,
    section_text: str,
    source_keyword: str,
    raw_match: str,
    source_snippet: str,
) -> ExtractedMetric:
    numeric_value, scale = _normalize_amount(raw_match)
    unit = _infer_unit(section_text)
    if unit is None and scale is not None:
        unit = f"{scale}_usd"

    return ExtractedMetric(
        value=numeric_value,
        numeric_value=numeric_value,
        raw_value=raw_match,
        unit=unit,
        source_keyword=source_keyword,
        source_snippet=source_snippet.strip(),
        section=SECTION_LABEL,
        raw_match=raw_match,
    )


def _extract_snippet_from_lines(lines: list[str], start_index: int, end_index: int) -> str:
    snippet_lines = lines[start_index : end_index + 1]
    snippet = " ".join(snippet_lines).strip()
    return re.sub(r"\s+", " ", snippet)


def _extract_metric_from_lines(
    lines: list[str],
    keywords: tuple[str, ...],
    section_text: str,
) -> ExtractedMetric | None:
    for keyword in keywords:
        keyword_pattern = _build_keyword_search_pattern(keyword)
        if keyword_pattern is None:
            continue

        for index, line in enumerate(lines):
            if keyword_pattern.search(line) is None:
                continue
            if "revenue" in keyword and _is_excluded_revenue_line(line):
                continue

            for offset in range(4):
                candidate_index = index + offset
                if candidate_index >= len(lines):
                    break
                candidate_amount = _extract_amount_from_line(lines[candidate_index])
                if candidate_amount is None:
                    continue
                source_snippet = _extract_snippet_from_lines(lines, index, candidate_index)
                return _build_metric(
                    section_text=section_text,
                    source_keyword=keyword,
                    raw_match=candidate_amount,
                    source_snippet=source_snippet,
                )

    return None


def _collect_amounts_near_keyword(
    lines: list[str],
    keyword_index: int,
    *,
    window: int = 6,
) -> tuple[list[str], str]:
    collected_amounts: list[str] = []
    snippet_end = min(len(lines), keyword_index + window + 1)

    for candidate_index in range(keyword_index, snippet_end):
        candidate_line = lines[candidate_index]
        if re.search(r"^\d{4}$", candidate_line):
            continue
        collected_amounts.extend(_extract_amounts_from_line(candidate_line))
        if len(collected_amounts) >= 2:
            break

    source_snippet = _extract_snippet_from_lines(lines, keyword_index, min(len(lines) - 1, snippet_end - 1))
    return collected_amounts, source_snippet


def _extract_metric_and_previous_from_lines(
    metric_name: str,
    lines: list[str],
    keywords: tuple[str, ...],
    section_text: str,
) -> tuple[ExtractedMetric | None, ExtractedMetric | None]:
    for keyword in keywords:
        keyword_pattern = _build_keyword_search_pattern(keyword)
        if keyword_pattern is None:
            continue

        for index, line in enumerate(lines):
            if keyword_pattern.search(line) is None:
                continue
            if metric_name == "revenue" and _is_excluded_revenue_line(line):
                continue

            collected_amounts, source_snippet = _collect_amounts_near_keyword(lines, index)
            if not collected_amounts:
                continue

            current_metric = _build_metric(
                section_text=section_text,
                source_keyword=keyword,
                raw_match=collected_amounts[0],
                source_snippet=source_snippet,
            )
            previous_metric = None
            if len(collected_amounts) >= 2:
                previous_metric = _build_metric(
                    section_text=section_text,
                    source_keyword=keyword,
                    raw_match=collected_amounts[1],
                    source_snippet=source_snippet,
                )
            return current_metric, previous_metric

    return None, None


def _extract_revenue_metric(section_text: str) -> ExtractedMetric | None:
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    explicit_revenue_keywords = (
        "total revenues",
        "total revenue",
        "net revenues",
        "net revenue",
        "net sales",
    )
    explicit_match = _extract_metric_from_lines(lines, explicit_revenue_keywords, section_text)
    if explicit_match is not None:
        return explicit_match

    revenue_line_keywords = ("revenues", "revenue")
    for keyword in revenue_line_keywords:
        keyword_pattern = _build_keyword_search_pattern(keyword)
        if keyword_pattern is None:
            continue

        for index, line in enumerate(lines):
            lowered_line = line.lower()
            if keyword_pattern.search(line) is None:
                continue
            if _is_excluded_revenue_line(line):
                continue
            if any(token in lowered_line for token in ("cost", "share", "tax", "internal revenue service")):
                continue

            candidate_amount = _extract_amount_from_line(line)
            if candidate_amount is not None:
                return _build_metric(
                    section_text=section_text,
                    source_keyword=keyword,
                    raw_match=candidate_amount,
                    source_snippet=line,
                )

            for offset in range(1, 4):
                candidate_index = index + offset
                if candidate_index >= len(lines):
                    break
                candidate_line = lines[candidate_index]
                if re.search(r"^\d{4}$", candidate_line):
                    continue
                candidate_amount = _extract_amount_from_line(candidate_line)
                if candidate_amount is None:
                    continue
                source_snippet = _extract_snippet_from_lines(lines, index, candidate_index)
                return _build_metric(
                    section_text=section_text,
                    source_keyword=keyword,
                    raw_match=candidate_amount,
                    source_snippet=source_snippet,
                )

    return None


def _extract_revenue_metrics(section_text: str) -> tuple[ExtractedMetric | None, ExtractedMetric | None]:
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    explicit_revenue_keywords = (
        "total revenues",
        "total revenue",
        "net revenues",
        "net revenue",
        "net sales",
    )
    explicit_current, explicit_previous = _extract_metric_and_previous_from_lines(
        "revenue",
        lines,
        explicit_revenue_keywords,
        section_text,
    )
    if explicit_current is not None:
        return explicit_current, explicit_previous

    revenue_line_keywords = ("revenues", "revenue")
    for keyword in revenue_line_keywords:
        keyword_pattern = _build_keyword_search_pattern(keyword)
        if keyword_pattern is None:
            continue

        for index, line in enumerate(lines):
            lowered_line = line.lower()
            if keyword_pattern.search(line) is None:
                continue
            if _is_excluded_revenue_line(line):
                continue
            if any(token in lowered_line for token in ("cost", "share", "tax", "internal revenue service")):
                continue

            collected_amounts, source_snippet = _collect_amounts_near_keyword(lines, index)
            if not collected_amounts:
                continue

            current_metric = _build_metric(
                section_text=section_text,
                source_keyword=keyword,
                raw_match=collected_amounts[0],
                source_snippet=source_snippet,
            )
            previous_metric = None
            if len(collected_amounts) >= 2:
                previous_metric = _build_metric(
                    section_text=section_text,
                    source_keyword=keyword,
                    raw_match=collected_amounts[1],
                    source_snippet=source_snippet,
                )
            return current_metric, previous_metric

    return None, None


def _extract_metric(section_text: str, keywords: tuple[str, ...]) -> ExtractedMetric | None:
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    line_match = _extract_metric_from_lines(lines, keywords, section_text)
    if line_match is not None:
        return line_match

    for keyword in keywords:
        keyword_pattern = _build_keyword_amount_pattern(keyword)
        if keyword_pattern is None:
            continue
        match = keyword_pattern.search(section_text)
        if match is None:
            continue

        snippet_start = max(0, match.start() - SNIPPET_WINDOW // 2)
        snippet_end = min(len(section_text), match.end() + SNIPPET_WINDOW // 2)
        source_snippet = section_text[snippet_start:snippet_end].replace("\n", " ").strip()
        return _build_metric(
            section_text=section_text,
            source_keyword=keyword,
            raw_match=match.group(1).strip(),
            source_snippet=source_snippet,
        )

    return None


def extract_financial_metrics(parsed_filing: ParsedFiling) -> dict[str, ExtractedMetric | None]:
    """Extract structured financial metrics from the financials section."""
    financials_text = parsed_filing.sections.get(SECTION_LABEL, "")
    metrics: dict[str, ExtractedMetric | None] = {}
    lines = [line.strip() for line in financials_text.splitlines() if line.strip()]

    revenue_metric, previous_revenue_metric = _extract_revenue_metrics(financials_text)
    metrics["revenue"] = revenue_metric
    metrics["previous_revenue"] = previous_revenue_metric

    for metric_name, keywords in FINANCIAL_FIELD_PATTERNS.items():
        if metric_name == "revenue":
            continue
        if metric_name in GROWTH_BASE_FIELDS:
            current_metric, previous_metric = _extract_metric_and_previous_from_lines(
                metric_name,
                lines,
                keywords,
                financials_text,
            )
            metrics[metric_name] = current_metric
            metrics[f"previous_{metric_name}"] = previous_metric
            continue
        metrics[metric_name] = _extract_metric(financials_text, keywords)

    return metrics
