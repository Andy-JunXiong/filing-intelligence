from app.schemas import CompanyInsight, PipelineStageResult


def export_insight(company_insight: CompanyInsight) -> PipelineStageResult:
    """Return placeholder export metadata for the output stage."""
    return PipelineStageResult(
        stage="export",
        payload={
            "company": company_insight.company,
            "format": "json",
            "status": "placeholder-exported",
        },
    )
