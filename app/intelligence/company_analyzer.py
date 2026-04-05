from app.schemas import CompanyInsight, CompanySignal


def build_company_insight(company_signal: CompanySignal) -> CompanyInsight:
    """Convert placeholder signals into a placeholder company insight."""
    return CompanyInsight(
        company=company_signal.company,
        filing_period=company_signal.filing_date,
        key_changes=["placeholder key change"],
        ai_strategy_summary="placeholder AI strategy summary",
        risk_summary="placeholder risk summary",
        watch_items=["placeholder watch item"],
    )
