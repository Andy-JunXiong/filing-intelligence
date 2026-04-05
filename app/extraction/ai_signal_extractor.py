from app.schemas import CompanySignal, ParsedFiling


def extract_signals(parsed_filing: ParsedFiling) -> CompanySignal:
    """Return placeholder signals for the extraction stage."""
    return CompanySignal(
        company=parsed_filing.metadata.company,
        filing_date=parsed_filing.metadata.filing_date,
        financial_metrics={
            "revenue": "placeholder",
            "operating_income": "placeholder",
        },
        ai_signals={
            "ai_mentions": "placeholder",
            "infrastructure_mentions": "placeholder",
        },
        risk_signals={
            "regulatory": "placeholder",
            "competition": "placeholder",
        },
        narrative_signals={
            "growth_drivers": "placeholder",
            "outlook": "placeholder",
        },
    )
