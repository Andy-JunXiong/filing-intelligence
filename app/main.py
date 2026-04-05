from __future__ import annotations

import argparse

from app.exporters import export_insight
from app.extraction import extract_financial_metrics, extract_signals
from app.ingestion import (
    fetch_latest_filing,
    fetch_sec_filing,
    get_watchlist_companies,
    store_raw_filing,
)
from app.intelligence import build_company_insight
from app.parsing import parse_filing
from app.schemas import PipelineStageResult


def run_mock_pipeline() -> list[PipelineStageResult]:
    companies = get_watchlist_companies()

    print("Watchlist:")
    for company in companies:
        print(f"- {company.name} ({company.ticker})")

    print("\nPipeline:")
    results: list[PipelineStageResult] = []

    for company in companies:
        raw_filing = fetch_latest_filing(company)
        stored_filing = store_raw_filing(raw_filing)
        parsed_filing = parse_filing(stored_filing)
        found_sections = [
            section_name
            for section_name, section_text in parsed_filing.sections.items()
            if section_text
        ]

        print(f"\nParsed filing for {company.ticker}")
        print(f"Sections found: {', '.join(found_sections) if found_sections else 'none'}")
        financial_metrics = extract_financial_metrics(parsed_filing)
        print(f"Extracted financial metrics: {financial_metrics}")

        company_signal = extract_signals(parsed_filing)
        company_insight = build_company_insight(company_signal)
        export_result = export_insight(company_insight)
        results.append(export_result)

        print(f"- {company.name}: ingestion -> parsing -> extraction -> intelligence -> export")

    return results


def run_real_ingestion() -> str:
    """Download one real SEC filing and save it locally."""
    companies = get_watchlist_companies()
    target_company = next(
        (company for company in companies if company.ticker == "MSFT"),
        companies[0],
    )
    filing_type = (
        target_company.filing_types[0] if target_company.filing_types else "10-K"
    )

    print(f"Real SEC ingestion for {target_company.ticker} ({filing_type})")
    raw_filing = fetch_sec_filing(target_company, filing_type=filing_type)
    stored_filing = store_raw_filing(raw_filing)
    print(f"Saved real filing to: {stored_filing.storage_path}")

    return stored_filing.storage_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the filing intelligence pipeline.")
    parser.add_argument(
        "--mode",
        choices=("mock", "real"),
        default="mock",
        help="Run the local mock pipeline or minimal real SEC ingestion.",
    )
    return parser


def main() -> list[PipelineStageResult] | str:
    args = build_parser().parse_args()
    if args.mode == "real":
        return run_real_ingestion()

    return run_mock_pipeline()


if __name__ == "__main__":
    main()
