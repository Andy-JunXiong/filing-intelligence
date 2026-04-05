import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.exporters import export_extracted_metrics
from app.extraction.financial_extractor import _extract_metric, extract_financial_metrics
from app.parsing.filing_parser import parse_filing
from app.schemas import FilingMetadata, RawFiling


class RealParsingCompatibilityTests(unittest.TestCase):
    def test_parse_filing_recognizes_real_section_heading_variants(self) -> None:
        raw_text = """
        <html><body>
        <p>PART I</p>
        <p>ITEM 1. B USINESS</p>
        <p>Cloud and productivity overview.</p>
        <p>ITEM 1A.</p>
        <p>Risk Factors</p>
        <p>Macro and competition risks.</p>
        <p>ITEM 7.</p>
        <p>Management's Discussion and Analysis of Financial Condition and Results of Operations</p>
        <p>Management discussion content.</p>
        <p>ITEM 8.</p>
        <p>Financial Statements and Supplementary Data</p>
        <p>Revenue 281,724 245,122</p>
        <p>Operating income 128,528 109,433</p>
        <p>Net income 101,832 88,136</p>
        <p>Additions to property and equipment 44,477 31,592</p>
        </body></html>
        """
        raw_filing = RawFiling(
            metadata=FilingMetadata(
                company="Microsoft",
                ticker="MSFT",
                filing_type="10-K",
                filing_date="2025-07-30",
                source_url="local",
            ),
            content=raw_text,
            storage_path="",
        )

        parsed_filing = parse_filing(raw_filing)

        self.assertIn("Cloud and productivity overview.", parsed_filing.sections["business"])
        self.assertIn("Macro and competition risks.", parsed_filing.sections["risk_factors"])
        self.assertIn("Management discussion content.", parsed_filing.sections["mda"])
        self.assertIn("Revenue 281,724 245,122", parsed_filing.sections["financials"])

    def test_extract_financial_metrics_returns_none_when_missing(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="Microsoft",
                    ticker="MSFT",
                    filing_type="10-K",
                    filing_date="2025-07-30",
                    source_url="local",
                ),
                content="<p>ITEM 8.</p><p>Financial Statements and Supplementary Data</p><p>No numeric metrics here.</p>",
                storage_path="",
            )
        )

        self.assertEqual(
            extract_financial_metrics(parsed_filing),
            {
                "revenue": None,
                "previous_revenue": None,
                "operating_income": None,
                "previous_operating_income": None,
                "net_income": None,
                "previous_net_income": None,
                "capex": None,
            },
        )

    def test_extract_financial_metrics_reads_structured_values(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="Microsoft",
                    ticker="MSFT",
                    filing_type="10-K",
                    filing_date="2025-07-30",
                    source_url="local",
                ),
                content="""
                <p>ITEM 8.</p>
                <p>Financial Statements and Supplementary Data</p>
                <p>(In millions, except per share amounts)</p>
                <p>Total revenue 281,724 245,122 211,915</p>
                <p>Operating income 128,528 109,433 88,523</p>
                <p>Net income 101,832 88,136 72,361</p>
                <p>Additions to property and equipment 44,477 31,592 28,107</p>
                """,
                storage_path="",
            )
        )

        metrics = extract_financial_metrics(parsed_filing)
        revenue = metrics["revenue"]

        self.assertIsNotNone(revenue)
        assert revenue is not None
        self.assertEqual(revenue.raw_value, "281,724")
        self.assertEqual(revenue.numeric_value, 281724)
        self.assertEqual(revenue.value, 281724)
        self.assertEqual(revenue.unit, "million_usd")
        self.assertEqual(revenue.source_keyword, "total revenue")
        self.assertIn("Total revenue 281,724", revenue.source_snippet)
        self.assertEqual(revenue.section, "financials")
        self.assertEqual(revenue.raw_match, "281,724")
        previous_revenue = metrics["previous_revenue"]
        self.assertIsNotNone(previous_revenue)
        assert previous_revenue is not None
        self.assertEqual(previous_revenue.numeric_value, 245122)

        previous_operating_income = metrics["previous_operating_income"]
        self.assertIsNotNone(previous_operating_income)
        assert previous_operating_income is not None
        self.assertEqual(previous_operating_income.numeric_value, 109433)

        previous_net_income = metrics["previous_net_income"]
        self.assertIsNotNone(previous_net_income)
        assert previous_net_income is not None
        self.assertEqual(previous_net_income.numeric_value, 88136)

    def test_extract_metric_ignores_pattern_errors_in_keyword_regex(self) -> None:
        pattern_error = getattr(__import__("re"), "PatternError", __import__("re").error)

        with patch(
            "app.extraction.financial_extractor._extract_metric_from_lines",
            return_value=None,
        ), patch(
            "app.extraction.financial_extractor.re.compile",
            side_effect=pattern_error("bad pattern"),
        ):
            self.assertIsNone(_extract_metric("Revenue: 281,724", ("revenue",)))

    def test_extract_financial_metrics_prefers_total_revenue_over_segment_revenue(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="Microsoft",
                    ticker="MSFT",
                    filing_type="10-K",
                    filing_date="2025-07-30",
                    source_url="local",
                ),
                content="""
                <p>ITEM 8.</p>
                <p>Financial Statements and Supplementary Data</p>
                <p>(In millions, except per share amounts)</p>
                <p>Revenue:</p>
                <p>Product 63,946</p>
                <p>Service and other 217,778</p>
                <p>Total revenue 281,724</p>
                """,
                storage_path="",
            )
        )

        metrics = extract_financial_metrics(parsed_filing)
        revenue = metrics["revenue"]
        self.assertIsNotNone(revenue)
        assert revenue is not None
        self.assertEqual(revenue.numeric_value, 281724)
        self.assertEqual(revenue.source_keyword, "total revenue")

    def test_extract_financial_metrics_skips_year_headers_before_capex_amount(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="Microsoft",
                    ticker="MSFT",
                    filing_type="10-K",
                    filing_date="2025-07-30",
                    source_url="local",
                ),
                content="""
                <p>ITEM 8.</p>
                <p>Financial Statements and Supplementary Data</p>
                <p>(In millions, except per share amounts)</p>
                <p>Year Ended June 30,</p>
                <p>2025</p>
                <p>2024</p>
                <p>Additions to property and equipment</p>
                <p>64,551</p>
                <p>44,477</p>
                """,
                storage_path="",
            )
        )

        metrics = extract_financial_metrics(parsed_filing)
        capex = metrics["capex"]
        self.assertIsNotNone(capex)
        assert capex is not None
        self.assertEqual(capex.numeric_value, 64551)
        self.assertIn("Additions to property and equipment", capex.source_snippet)

    def test_extract_financial_metrics_supports_nvda_style_capex_phrase(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="NVIDIA",
                    ticker="NVDA",
                    filing_type="10-K",
                    filing_date="2025-02-26",
                    source_url="local",
                ),
                content="""
                <p>ITEM 8.</p>
                <p>Financial Statements and Supplementary Data</p>
                <p>(In millions, except per share amounts)</p>
                <p>Purchases related to property and equipment and intangible assets</p>
                <p>( 3,236 )</p>
                <p>( 1,069 )</p>
                """,
                storage_path="",
            )
        )

        metrics = extract_financial_metrics(parsed_filing)
        capex = metrics["capex"]
        self.assertIsNotNone(capex)
        assert capex is not None
        self.assertEqual(capex.numeric_value, 3236)
        self.assertEqual(capex.source_keyword, "purchases related to property and equipment")

    def test_extract_financial_metrics_supports_googl_total_revenues(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="Alphabet",
                    ticker="GOOGL",
                    filing_type="10-K",
                    filing_date="2025-02-05",
                    source_url="local",
                ),
                content="""
                <p>ITEM 8.</p>
                <p>Financial Statements and Supplementary Data</p>
                <p>(In millions, except per share amounts)</p>
                <p>Accrued revenue share 8,876</p>
                <p>Total revenues 350,018 307,394 282,836</p>
                <p>Income from operations 112,390 84,293 74,842</p>
                <p>Net income 100,118 73,795 59,972</p>
                <p>Purchases of property and equipment (31,485)</p>
                """,
                storage_path="",
            )
        )

        metrics = extract_financial_metrics(parsed_filing)
        revenue = metrics["revenue"]
        self.assertIsNotNone(revenue)
        assert revenue is not None
        self.assertEqual(revenue.numeric_value, 350018)
        self.assertEqual(revenue.source_keyword, "total revenues")
        previous_revenue = metrics["previous_revenue"]
        self.assertIsNotNone(previous_revenue)
        assert previous_revenue is not None
        self.assertEqual(previous_revenue.numeric_value, 307394)

    def test_extract_financial_metrics_avoids_meta_non_statement_revenue_mentions(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="Meta Platforms",
                    ticker="META",
                    filing_type="10-K",
                    filing_date="2025-01-30",
                    source_url="local",
                ),
                content="""
                <p>ITEM 8.</p>
                <p>Financial Statements and Supplementary Data</p>
                <p>(In millions, except per share amounts)</p>
                <p>As discussed in Note 15, the Internal Revenue Service reviewed certain periods.</p>
                <p>Revenue 164,501 134,902 116,609</p>
                <p>Income from operations 69,380 46,751 28,944</p>
                <p>Net income 62,360 39,098 23,200</p>
                <p>Purchases of property and equipment (37,256)</p>
                """,
                storage_path="",
            )
        )

        metrics = extract_financial_metrics(parsed_filing)
        revenue = metrics["revenue"]
        self.assertIsNotNone(revenue)
        assert revenue is not None
        self.assertEqual(revenue.numeric_value, 164501)
        self.assertIn("Revenue 164,501", revenue.source_snippet)
        previous_revenue = metrics["previous_revenue"]
        self.assertIsNotNone(previous_revenue)
        assert previous_revenue is not None
        self.assertEqual(previous_revenue.numeric_value, 134902)

    def test_export_extracted_metrics_writes_json_file(self) -> None:
        parsed_filing = parse_filing(
            RawFiling(
                metadata=FilingMetadata(
                    company="Microsoft",
                    ticker="MSFT",
                    filing_type="10-K",
                    filing_date="2025-07-30",
                    source_url="local",
                ),
                content="""
                <p>ITEM 8.</p>
                <p>Financial Statements and Supplementary Data</p>
                <p>(In millions, except per share amounts)</p>
                <p>Total revenue 281,724</p>
                """,
                storage_path="",
            )
        )
        metrics = extract_financial_metrics(parsed_filing)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = export_extracted_metrics(
                parsed_filing.metadata,
                metrics,
                output_dir=Path(temp_dir),
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertTrue(output_path.name.endswith("MSFT_10-K_2025-07-30.json"))
        self.assertEqual(payload["ticker"], "MSFT")
        self.assertEqual(payload["financial_metrics"]["revenue"]["numeric_value"], 281724)
        self.assertIn(
            "Total revenue 281,724",
            payload["financial_metrics"]["revenue"]["source_snippet"],
        )


if __name__ == "__main__":
    unittest.main()
