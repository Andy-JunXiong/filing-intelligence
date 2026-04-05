from __future__ import annotations

import html
import re


BLOCK_TAG_PATTERN = re.compile(r"(?is)<\s*/?\s*(?:div|p|tr|td|th|li|br|table|h[1-6])\b[^>]*>")
COMMENT_PATTERN = re.compile(r"(?is)<!--.*?-->")
SCRIPT_STYLE_PATTERN = re.compile(r"(?is)<(script|style)\b.*?>.*?</\1>")
TAG_PATTERN = re.compile(r"(?is)<[^>]+>")


def _strip_html_markup(raw_text: str) -> str:
    """Convert SEC HTML filings into plain text while preserving block breaks."""
    without_comments = COMMENT_PATTERN.sub(" ", raw_text)
    without_script_blocks = SCRIPT_STYLE_PATTERN.sub(" ", without_comments)
    with_breaks = BLOCK_TAG_PATTERN.sub("\n", without_script_blocks)
    without_tags = TAG_PATTERN.sub(" ", with_breaks)
    return html.unescape(without_tags)


def clean_text(raw_text: str) -> str:
    """Normalize raw filing text for downstream section parsing."""
    normalized = _strip_html_markup(raw_text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\t", " ")
    normalized = normalized.replace("\xa0", " ")
    normalized = normalized.replace("\u2019", "'").replace("\u2018", "'")
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')

    cleaned_lines: list[str] = []
    previous_blank = False

    for line in normalized.split("\n"):
        compact_line = re.sub(r"\s+", " ", line).strip()

        if not compact_line:
            if not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue

        cleaned_lines.append(compact_line)
        previous_blank = False

    return "\n".join(cleaned_lines).strip()
