from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WatchlistCompany:
    company_name: str
    ticker: str
    cik: str = ""
    filing_types: tuple[str, ...] = field(default_factory=tuple)

    @property
    def name(self) -> str:
        """Backward-compatible alias for existing pipeline code."""
        return self.company_name


@dataclass(frozen=True)
class FilingMetadata:
    company: str
    ticker: str
    filing_type: str
    filing_date: str
    source_url: str


@dataclass(frozen=True)
class RawFiling:
    metadata: FilingMetadata
    content: str
    storage_path: str


@dataclass(frozen=True)
class ParsedFiling:
    metadata: FilingMetadata
    full_text: str
    sections: dict[str, str]


@dataclass(frozen=True)
class PipelineStageResult:
    stage: str
    payload: dict[str, Any]
