from __future__ import annotations

import re


SECTION_ORDER = ["business", "mda", "risk_factors", "financials"]
SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "business": ("business", "item 1. business"),
    "mda": (
        "mda",
        "md&a",
        "management discussion and analysis",
        "management's discussion and analysis",
        "management discussion & analysis",
    ),
    "risk_factors": ("risk factors", "item 1a. risk factors"),
    "financials": (
        "financial statements",
        "financials",
        "item 8. financial statements",
    ),
}


def _normalize_heading(line: str) -> str:
    lowered = line.lower().strip()
    lowered = re.sub(r"[^a-z0-9&.\s']", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _match_section(line: str) -> str | None:
    normalized_line = _normalize_heading(line)

    for section_name, patterns in SECTION_PATTERNS.items():
        if normalized_line in patterns:
            return section_name

    return None


def split_into_sections(text: str) -> dict[str, str]:
    """Split cleaned filing text into minimal placeholder sections."""
    sections = {section_name: "" for section_name in SECTION_ORDER}
    current_section: str | None = None
    section_lines: dict[str, list[str]] = {section_name: [] for section_name in SECTION_ORDER}

    for line in text.splitlines():
        matched_section = _match_section(line)
        if matched_section is not None:
            current_section = matched_section
            continue

        if current_section is not None:
            section_lines[current_section].append(line)

    for section_name in SECTION_ORDER:
        sections[section_name] = "\n".join(section_lines[section_name]).strip()

    return sections
