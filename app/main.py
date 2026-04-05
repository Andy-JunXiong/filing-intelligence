from __future__ import annotations

import argparse

from app.exporters import build_extracted_metrics_payload, export_extracted_metrics, export_insight
from app.extraction import extract_financial_metrics, extract_signals
from app.extraction.financial_extractor import get_financials_section_preview
from app.ingestion import fetch_latest_filing, fetch_sec_filing, get_watchlist_companies, store_raw_filing
from app.intelligence import (
    build_company_comparison,
    build_multi_company_comparison,
    build_company_insight,
    build_multi_year_trajectory,
    build_structured_insight,
    export_company_comparison,
    export_company_comparison_markdown,
    export_industry_intelligence_report_markdown,
    export_multi_company_comparison,
    export_multi_company_comparison_markdown,
    export_multi_year_trajectory_markdown,
    export_strategic_intelligence_report_markdown,
    export_structured_insight,
    export_visual_intelligence_markdown,
    export_visualization_datasets,
)
from app.parsing import parse_filing
from app.schemas import PipelineStageResult, WatchlistCompany
from signals.financial_signals import build_financial_signals, export_financial_signals


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


def _resolve_company(ticker: str) -> WatchlistCompany:
    companies = get_watchlist_companies()
    normalized_ticker = ticker.upper()
    target_company = next((company for company in companies if company.ticker == normalized_ticker), None)
    if target_company is None:
        available = ", ".join(company.ticker for company in companies)
        raise ValueError(f"Unknown ticker '{ticker}'. Available tickers: {available}")
    return target_company


def _run_real_pipeline_for_company(
    ticker: str,
    filing_type: str | None = None,
    filing_year: str | None = None,
    filing_date: str | None = None,
) -> dict[str, object]:
    target_company = _resolve_company(ticker)
    selected_filing_type = filing_type or (
        target_company.filing_types[0] if target_company.filing_types else "10-K"
    )

    print(f"Real SEC ingestion for {target_company.ticker} ({selected_filing_type})")
    raw_filing = fetch_sec_filing(
        target_company,
        filing_type=selected_filing_type,
        filing_year=filing_year,
        filing_date=filing_date,
    )
    stored_filing = store_raw_filing(raw_filing)
    print(f"Saved real filing to: {stored_filing.storage_path}")

    parsed_filing = parse_filing(stored_filing)
    found_sections = [
        section_name
        for section_name, section_text in parsed_filing.sections.items()
        if section_text
    ]
    financials_preview = get_financials_section_preview(parsed_filing)
    financial_metrics = extract_financial_metrics(parsed_filing)
    extracted_output_path = export_extracted_metrics(parsed_filing.metadata, financial_metrics)
    extracted_payload = build_extracted_metrics_payload(parsed_filing.metadata, financial_metrics)
    financial_signals = build_financial_signals(extracted_payload)
    signals_output_path = export_financial_signals(financial_signals)
    structured_insight = build_structured_insight(extracted_payload, financial_signals)
    insight_output_path = export_structured_insight(structured_insight)

    print(f"Parsed filing for {target_company.ticker}")
    print(f"Sections found: {', '.join(found_sections) if found_sections else 'none'}")
    print(
        "Financials section preview: "
        f"{financials_preview if financials_preview else 'none'}"
    )
    print(f"Extracted financial metrics: {financial_metrics}")
    print(f"Extracted JSON saved to: {extracted_output_path}")
    print(f"Financial signals saved to: {signals_output_path}")
    print(f"Insight saved to: {insight_output_path}")

    print("Structured extraction preview:")
    for metric_name, metric in financial_metrics.items():
        if metric is None:
            print(f"- {metric_name}: none")
            continue
        snippet_preview = metric.source_snippet[:120]
        if len(metric.source_snippet) > 120:
            snippet_preview += "..."
        print(
            f"- {metric_name}: value={metric.value} unit={metric.unit or 'unknown'} "
            f"keyword={metric.source_keyword!r} snippet={snippet_preview!r}"
        )

    print("Financial signals preview:")
    print(financial_signals)
    print("Insight takeaways preview:")
    for takeaway in structured_insight.get("takeaways", [])[:2]:
        if isinstance(takeaway, dict):
            print(f"- {takeaway.get('text')}")
        else:
            print(f"- {takeaway}")

    return {
        "ticker": target_company.ticker,
        "filing_type": selected_filing_type,
        "filing_date": parsed_filing.metadata.filing_date,
        "extracted_payload": extracted_payload,
        "signals_payload": financial_signals,
        "insight_payload": structured_insight,
        "extracted_output_path": str(extracted_output_path),
        "signals_output_path": str(signals_output_path),
        "insight_output_path": str(insight_output_path),
    }


def run_real_ingestion(
    ticker: str = "MSFT",
    filing_type: str | None = None,
    filing_year: str | None = None,
    filing_date: str | None = None,
    compare_with: str | None = None,
    compare_many: list[str] | None = None,
    trajectory_years: list[str] | None = None,
) -> str:
    if trajectory_years:
        company_results = [
            _run_real_pipeline_for_company(
                ticker=ticker,
                filing_type=filing_type,
                filing_year=year,
                filing_date=filing_date,
            )
            for year in trajectory_years
        ]
        trajectory_payload = build_multi_year_trajectory(
            company=ticker.upper(),
            filing_type=filing_type or "10-K",
            yearly_payloads=company_results,
        )
        trajectory_output_path = export_multi_year_trajectory_markdown(trajectory_payload)
        print(f"Trajectory analysis saved to: {trajectory_output_path}")
        for key in ("revenue_trajectory", "margin_expansion", "capex_cycle"):
            insight = trajectory_payload.get("insights", {}).get(key)
            if isinstance(insight, str):
                print(f"- {insight}")
        return str(trajectory_output_path)

    if compare_many:
        company_results = [
            _run_real_pipeline_for_company(
                ticker=company_ticker,
                filing_type=filing_type,
                filing_year=filing_year,
                filing_date=filing_date,
            )
            for company_ticker in compare_many
        ]
        comparison_payload = build_multi_company_comparison(company_results)
        if comparison_payload.get("comparability", {}).get("same_filing_year") is not True:
            filing_dates = comparison_payload.get("filing_dates", {})
            raise ValueError(
                "Multi-company comparison requires the same filing year for all companies. "
                f"Got filing_dates={filing_dates}."
            )

        comparison_output_path = export_multi_company_comparison(comparison_payload)
        comparison_markdown_path = export_multi_company_comparison_markdown(comparison_payload)
        industry_report_path = export_industry_intelligence_report_markdown(comparison_payload)
        strategic_report_path = export_strategic_intelligence_report_markdown(comparison_payload)
        visualization_paths = export_visualization_datasets(comparison_payload)
        visual_report_path = export_visual_intelligence_markdown(comparison_payload)
        print(f"Comparison JSON saved to: {comparison_output_path}")
        print(f"Comparison markdown saved to: {comparison_markdown_path}")
        print(f"Industry report saved to: {industry_report_path}")
        print(f"Strategic report saved to: {strategic_report_path}")
        for dataset_name, dataset_path in visualization_paths.items():
            print(f"Visualization dataset saved to: {dataset_path} ({dataset_name})")
        print(f"Visual intelligence report saved to: {visual_report_path}")
        print("Comparison takeaways preview:")
        for takeaway in comparison_payload.get("takeaways", [])[:3]:
            print(f"- {takeaway}")
        return str(comparison_output_path)

    primary_result = _run_real_pipeline_for_company(
        ticker=ticker,
        filing_type=filing_type,
        filing_year=filing_year,
        filing_date=filing_date,
    )

    if not compare_with:
        return str(primary_result["insight_output_path"])

    secondary_result = _run_real_pipeline_for_company(
        ticker=compare_with,
        filing_type=filing_type,
        filing_year=filing_year,
        filing_date=filing_date,
    )
    comparison_payload = build_company_comparison(
        primary_result["extracted_payload"],
        primary_result["signals_payload"],
        primary_result["insight_payload"],
        secondary_result["extracted_payload"],
        secondary_result["signals_payload"],
        secondary_result["insight_payload"],
    )
    if comparison_payload.get("comparability", {}).get("same_filing_year") is not True:
        primary_date = primary_result["filing_date"]
        secondary_date = secondary_result["filing_date"]
        raise ValueError(
            "Comparison requires the same filing year for both companies. "
            f"Got {ticker.upper()}={primary_date} and {compare_with.upper()}={secondary_date}."
        )

    comparison_output_path = export_company_comparison(comparison_payload)
    comparison_markdown_path = export_company_comparison_markdown(comparison_payload)

    print(f"Comparison JSON saved to: {comparison_output_path}")
    print(f"Comparison markdown saved to: {comparison_markdown_path}")
    print("Comparison takeaways preview:")
    for takeaway in comparison_payload.get("takeaways", [])[:2]:
        print(f"- {takeaway}")

    return str(comparison_output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the filing intelligence pipeline.")
    parser.add_argument(
        "--mode",
        choices=("mock", "real"),
        default="mock",
        help="Run the local mock pipeline or minimal real SEC ingestion.",
    )
    parser.add_argument(
        "--ticker",
        default="MSFT",
        help="Primary ticker to run in real mode (default: MSFT).",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("LEFT_TICKER", "RIGHT_TICKER"),
        default=None,
        help="Run comparison mode for two tickers, for example --compare MSFT NVDA.",
    )
    parser.add_argument(
        "--compare-many",
        nargs="+",
        metavar="TICKER",
        default=None,
        help="Run multi-company comparison mode, for example --compare-many MSFT NVDA AMZN GOOGL META.",
    )
    parser.add_argument(
        "--trajectory",
        nargs="+",
        metavar="YEAR",
        default=None,
        help="Run multi-year trajectory analysis for the primary ticker, for example --ticker NVDA --trajectory 2023 2024 2025.",
    )
    parser.add_argument(
        "--compare-with",
        default=None,
        help="Backward-compatible second ticker option for real mode.",
    )
    parser.add_argument(
        "--filing-type",
        default=None,
        help="Optional filing type override, for example 10-K.",
    )
    parser.add_argument(
        "--filing-year",
        default=None,
        help="Optional filing year filter, for example 2025.",
    )
    parser.add_argument(
        "--filing-date",
        default=None,
        help="Optional filing date filter in YYYY-MM-DD format.",
    )
    return parser


def main() -> list[PipelineStageResult] | str:
    args = build_parser().parse_args()
    if args.mode == "real":
        ticker = args.ticker
        compare_with = args.compare_with
        if args.compare is not None:
            ticker, compare_with = args.compare

        return run_real_ingestion(
            ticker=ticker,
            filing_type=args.filing_type,
            filing_year=args.filing_year,
            filing_date=args.filing_date,
            compare_with=compare_with,
            compare_many=args.compare_many,
            trajectory_years=args.trajectory,
        )

    return run_mock_pipeline()


if __name__ == "__main__":
    main()
