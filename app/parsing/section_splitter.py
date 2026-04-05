from __future__ import annotations

import re


SECTION_ORDER = ["business", "mda", "risk_factors", "financials"]
SECTION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "business": (
        re.compile(r"^business$"),
        re.compile(r"^item\s*1\.?\s*business(?:\s|$)"),
    ),
    "mda": (
        re.compile(r"^md&a$"),
        re.compile(r"^mda$"),
        re.compile(r"^management'?s discussion and analysis(?:\s|$)"),
        re.compile(
            r"^item\s*7\.?\s*management'?s discussion and analysis(?: of financial condition and results of operations)?(?:\s|$)"
        ),
    ),
    "risk_factors": (
        re.compile(r"^risk factors$"),
        re.compile(r"^item\s*1a\.?\s*risk factors(?:\s|$)"),
    ),
    "financials": (
        re.compile(r"^financial statements(?: and supplementary data)?$"),
        re.compile(r"^financials$"),
        re.compile(
            r"^item\s*8\.?\s*financial statements(?: and supplementary data)?(?:\s|$)"
        ),
    ),
}
COMPACT_SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "business": ("business", "item1.business"),
    "mda": (
        "mda",
        "item7.managementsdiscussionandanalysis",
        "managementsdiscussionandanalysis",
    ),
    "risk_factors": ("riskfactors", "item1a.riskfactors"),
    "financials": (
        "financialstatements",
        "item8.financialstatements",
        "financialstatementsandsupplementarydata",
        "item8.financialstatementsandsupplementarydata",
    ),
}


def _normalize_heading(line: str) -> str:
    lowered = line.lower().strip()
    lowered = lowered.replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9.\s']", "", lowered)
    lowered = re.sub(r"\b([a-z]{1,3})\s+([a-z]{1,3})\s+([a-z]{2,})\b", r"\1\2\3", lowered)
    lowered = re.sub(r"\b([a-z]{1,3})\s+([a-z]{2,})\b", r"\1\2", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _match_section(line: str) -> str | None:
    normalized_line = _normalize_heading(line)
    compact_line = normalized_line.replace(" ", "").replace("'", "")

    for section_name, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(normalized_line):
                return section_name
        for compact_pattern in COMPACT_SECTION_PATTERNS[section_name]:
            if compact_line.startswith(compact_pattern):
                return section_name

    return None


def split_into_sections(text: str) -> dict[str, str]:
    """Split filing text into canonical sections when headings are found."""
    sections = {section_name: "" for section_name in SECTION_ORDER}
    lines = text.splitlines()
    matches: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        combined_line = line
        if index + 1 < len(lines):
            combined_line = f"{line} {lines[index + 1]}"

        matched_section = _match_section(combined_line) or _match_section(line)
        if matched_section is None:
            continue
        if matches and matches[-1][0] == index:
            continue
        matches.append((index, matched_section))

    section_candidates: dict[str, list[str]] = {
        section_name: [] for section_name in SECTION_ORDER
    }
    for match_index, (start_index, section_name) in enumerate(matches):
        end_index = matches[match_index + 1][0] if match_index + 1 < len(matches) else len(lines)
        candidate_text = "\n".join(lines[start_index + 1 : end_index]).strip()
        if candidate_text:
            section_candidates[section_name].append(candidate_text)

    for section_name in SECTION_ORDER:
        candidates = section_candidates[section_name]
        if candidates:
            sections[section_name] = max(candidates, key=len)

    return sections
