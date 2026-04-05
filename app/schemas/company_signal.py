from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompanySignal:
    company: str
    filing_date: str
    financial_metrics: dict[str, str] = field(default_factory=dict)
    ai_signals: dict[str, str] = field(default_factory=dict)
    risk_signals: dict[str, str] = field(default_factory=dict)
    narrative_signals: dict[str, str] = field(default_factory=dict)
