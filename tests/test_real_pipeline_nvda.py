import unittest
from pathlib import Path
from unittest.mock import patch

from app.main import run_real_ingestion
from app.schemas import FilingMetadata, RawFiling


class NvidiaRealPipelineTests(unittest.TestCase):
    def test_run_real_ingestion_supports_nvda_with_existing_pipeline(self) -> None:
        mock_filing = RawFiling(
            metadata=FilingMetadata(
                company="NVIDIA",
                ticker="NVDA",
                filing_type="10-K",
                filing_date="2025-02-21",
                source_url="local",
            ),
            content="""
            <p>ITEM 8.</p>
            <p>Financial Statements and Supplementary Data</p>
            <p>(In millions, except per share amounts)</p>
            <p>Total revenue 130,497</p>
            <p>Operating income 81,453</p>
            <p>Net income 72,880</p>
            <p>Additions to property and equipment 32,000</p>
            """,
            storage_path="",
        )

        insight_path = Path("data") / "insights" / "NVDA_10-K_2025.md"
        signals_path = Path("data") / "signals" / "NVDA_10-K_2025.json"
        extracted_path = Path("data") / "extracted" / "NVDA_10-K_2025-02-21.json"

        with patch("app.main.fetch_sec_filing", return_value=mock_filing), patch(
            "app.main.store_raw_filing", return_value=mock_filing
        ):
            returned_path = run_real_ingestion("NVDA")

        self.assertEqual(returned_path, str(insight_path))
        self.assertTrue(insight_path.exists())
        self.assertTrue(signals_path.exists())
        self.assertTrue(extracted_path.exists())
        self.assertIn("High profitability", insight_path.read_text(encoding="utf-8"))

        extracted_path.unlink(missing_ok=True)
        signals_path.unlink(missing_ok=True)
        insight_path.unlink(missing_ok=True)

    def test_run_real_ingestion_comparison_rejects_year_mismatch(self) -> None:
        msft_filing = RawFiling(
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
            <p>Operating income 128,528</p>
            <p>Net income 101,832</p>
            <p>Additions to property and equipment 64,551</p>
            """,
            storage_path="",
        )
        nvda_filing = RawFiling(
            metadata=FilingMetadata(
                company="NVIDIA",
                ticker="NVDA",
                filing_type="10-K",
                filing_date="2026-02-25",
                source_url="local",
            ),
            content="""
            <p>ITEM 8.</p>
            <p>Financial Statements and Supplementary Data</p>
            <p>(In millions, except per share amounts)</p>
            <p>Total revenue 130,497</p>
            <p>Operating income 81,453</p>
            <p>Net income 72,880</p>
            <p>Additions to property and equipment 3,236</p>
            """,
            storage_path="",
        )

        with patch(
            "app.main.fetch_sec_filing",
            side_effect=[msft_filing, nvda_filing],
        ), patch("app.main.store_raw_filing", side_effect=[msft_filing, nvda_filing]):
            with self.assertRaisesRegex(
                ValueError,
                "Comparison requires the same filing year for both companies",
            ):
                run_real_ingestion("MSFT", filing_type="10-K", compare_with="NVDA")


if __name__ == "__main__":
    unittest.main()
