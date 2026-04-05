import unittest

from app.config.settings import load_watchlist
from app.ingestion.company_registry import get_watchlist_companies


class WatchlistLoadingTests(unittest.TestCase):
    def test_load_watchlist_returns_expected_companies(self) -> None:
        companies = load_watchlist()

        self.assertEqual(len(companies), 5)
        self.assertEqual(companies[0].company_name, "Microsoft")
        self.assertEqual(companies[0].ticker, "MSFT")
        self.assertEqual(companies[0].cik, "0000789019")
        self.assertEqual(companies[0].filing_types, ("10-K", "10-Q"))
        self.assertEqual(companies[-1].company_name, "Meta Platforms")
        self.assertEqual(companies[-1].ticker, "META")

    def test_ingestion_registry_returns_company_list(self) -> None:
        companies = get_watchlist_companies()

        self.assertGreater(len(companies), 0)
        self.assertEqual(
            [company.ticker for company in companies],
            ["MSFT", "NVDA", "GOOGL", "AMZN", "META"],
        )


if __name__ == "__main__":
    unittest.main()
