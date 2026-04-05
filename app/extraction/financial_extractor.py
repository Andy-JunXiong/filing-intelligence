from __future__ import annotations

import re

from app.schemas import ParsedFiling


FINANCIAL_FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "revenue": ("total revenue", "net revenue", "revenue"),
    "operating_income": ("operating income", "income from operations"),
    "net_income": ("net income",),
    "capex": ("capital expenditures", "capex"),
}
AMOUNT_PATTERN = re.compile(
    r"(?i)\$?\d[\d,]*(?:\.\d+)?(?:\s*(?:million|billion|thousand))?"
)


def _extract_amount_from_line(line: str) -> str | None:
    amount_match = AMOUNT_PATTERN.search(line)
    if amount_match is None:
        return None

    return amount_match.group(0).strip()


def _extract_metric(section_text: str, keywords: tuple[str, ...]) -> str | None:
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    for line in lines:
        lowered_line = line.lower()
        if not any(keyword in lowered_line for keyword in keywords):
            continue

        amount = _extract_amount_from_line(line)
        if amount is not None:
            return amount

    for keyword in keywords:
        keyword_pattern = re.compile(
            rf"(?is){re.escape(keyword)}[^.\n:]*[:\-]?\s*({AMOUNT_PATTERN.pattern})"
        )
        match = keyword_pattern.search(section_text)
        if match is not None:
            return match.group(1).strip()

    return None


def extract_financial_metrics(parsed_filing: ParsedFiling) -> dict[str, str | None]:
    """Extract basic financial metrics from the financials section with simple rules."""
    financials_text = parsed_filing.sections.get("financials", "")

    return {
        metric_name: _extract_metric(financials_text, keywords)
        for metric_name, keywords in FINANCIAL_FIELD_PATTERNS.items()
    }
