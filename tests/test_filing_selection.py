import unittest

from app.ingestion import select_sec_filing_metadata
from app.schemas import WatchlistCompany


class FilingSelectionTests(unittest.TestCase):
    def test_select_sec_filing_metadata_prefers_requested_year(self) -> None:
        company = WatchlistCompany(company_name="NVIDIA", ticker="NVDA", cik="0001045810")
        recent_filings = {
            "form": ["10-K", "10-K", "10-Q"],
            "accessionNumber": ["0001-26", "0002-25", "0003-25"],
            "filingDate": ["2026-02-25", "2025-02-21", "2025-08-20"],
            "primaryDocument": ["nvda-20260125.htm", "nvda-20250126.htm", "nvda-q3.htm"],
        }

        metadata = select_sec_filing_metadata(
            company=company,
            recent_filings=recent_filings,
            filing_type="10-K",
            filing_year="2025",
        )

        self.assertEqual(metadata.filing_date, "2025-02-21")
        self.assertEqual(metadata.ticker, "NVDA")

    def test_select_sec_filing_metadata_can_match_exact_date(self) -> None:
        company = WatchlistCompany(company_name="Microsoft", ticker="MSFT", cik="0000789019")
        recent_filings = {
            "form": ["10-K", "10-K"],
            "accessionNumber": ["0001-25", "0002-24"],
            "filingDate": ["2025-07-30", "2024-07-30"],
            "primaryDocument": ["msft-20250630.htm", "msft-20240630.htm"],
        }

        metadata = select_sec_filing_metadata(
            company=company,
            recent_filings=recent_filings,
            filing_type="10-K",
            filing_year="2025",
            filing_date="2025-07-30",
        )

        self.assertEqual(metadata.filing_date, "2025-07-30")

    def test_select_sec_filing_metadata_raises_clear_error_when_year_missing(self) -> None:
        company = WatchlistCompany(company_name="Microsoft", ticker="MSFT", cik="0000789019")
        recent_filings = {
            "form": ["10-K", "10-K"],
            "accessionNumber": ["0001-25", "0002-24"],
            "filingDate": ["2025-07-30", "2024-07-30"],
            "primaryDocument": ["msft-20250630.htm", "msft-20240630.htm"],
        }

        with self.assertRaisesRegex(
            ValueError,
            "No recent filing found for MSFT matching 10-K, year=2023",
        ):
            select_sec_filing_metadata(
                company=company,
                recent_filings=recent_filings,
                filing_type="10-K",
                filing_year="2023",
            )


if __name__ == "__main__":
    unittest.main()
