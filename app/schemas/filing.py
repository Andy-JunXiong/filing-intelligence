from dataclasses import asdict, dataclass, field
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
class ExtractedMetric:
    value: int | float | None
    numeric_value: int | float | None
    raw_value: str | None
    unit: str | None
    source_keyword: str
    source_snippet: str
    section: str
    raw_match: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PipelineStageResult:
    stage: str
    payload: dict[str, Any]
