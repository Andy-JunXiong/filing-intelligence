from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompanyInsight:
    company: str
    filing_period: str
    key_changes: list[str] = field(default_factory=list)
    ai_strategy_summary: str = ""
    risk_summary: str = ""
    watch_items: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ComparisonReport:
    companies: list[str]
    summary_table: list[dict[str, str]] = field(default_factory=list)
    key_differences: list[str] = field(default_factory=list)
    ranking: list[str] = field(default_factory=list)
