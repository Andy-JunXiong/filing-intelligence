from __future__ import annotations

from pathlib import Path

from app.parsing.section_splitter import split_into_sections
from app.parsing.text_cleaner import clean_text
from app.schemas import ParsedFiling, RawFiling


def read_raw_filing_text(raw_filing: RawFiling) -> str:
    """Read filing text from disk when available, otherwise fall back to in-memory content."""
    if raw_filing.storage_path:
        storage_path = Path(raw_filing.storage_path)
        if storage_path.exists():
            return storage_path.read_text(encoding="utf-8")

    return raw_filing.content


def parse_filing(raw_filing: RawFiling) -> ParsedFiling:
    """Parse a stored raw filing into cleaned text and best-effort sections."""
    raw_text = read_raw_filing_text(raw_filing)
    cleaned_text = clean_text(raw_text)
    sections = split_into_sections(cleaned_text)

    return ParsedFiling(
        metadata=raw_filing.metadata,
        full_text=cleaned_text,
        sections=sections,
    )
