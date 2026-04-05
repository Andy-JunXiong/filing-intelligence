import unittest
from pathlib import Path

from app.intelligence.comparison_engine import build_multi_company_comparison
from app.intelligence.industry_report import export_industry_intelligence_report_markdown


class IndustryReportTests(unittest.TestCase):
    OUTPUT_DIR = Path("test_tmp") / "industry_report"

    def _multi_company_payloads(self) -> list[dict[str, object]]:
        return [
            {
                "ticker": "MSFT",
                "filing_date": "2025-07-30",
                "extracted_payload": {
                    "ticker": "MSFT",
                    "filing_type": "10-K",
                    "filing_date": "2025-07-30",
                    "financial_metrics": {"revenue": {"numeric_value": 281724}},
                },
                "signals_payload": {
                    "company": "MSFT",
                    "metrics": {
                        "operating_margin": 0.456,
                        "net_margin": 0.361,
                        "capex_ratio": 0.229,
                        "revenue_growth": 0.149,
                        "operating_income_growth": 0.175,
                        "net_income_growth": 0.156,
                    },
                    "signals": [
                        {"signal": "AI Infrastructure Builder"},
                        {"signal": "AI Platform Scale"},
                    ],
                },
                "insight_payload": {"takeaways": [{"text": "MSFT takeaway"}]},
            },
            {
                "ticker": "NVDA",
                "filing_date": "2025-02-26",
                "extracted_payload": {
                    "ticker": "NVDA",
                    "filing_type": "10-K",
                    "filing_date": "2025-02-26",
                    "financial_metrics": {"revenue": {"numeric_value": 130497}},
                },
                "signals_payload": {
                    "company": "NVDA",
                    "metrics": {
                        "operating_margin": 0.624,
                        "net_margin": 0.558,
                        "capex_ratio": 0.025,
                        "revenue_growth": 1.142,
                        "operating_income_growth": 1.471,
                        "net_income_growth": 1.449,
                    },
                    "signals": [
                        {"signal": "AI Hardware Platform"},
                    ],
                },
                "insight_payload": {"takeaways": [{"text": "NVDA takeaway"}]},
            },
            {
                "ticker": "AMZN",
                "filing_date": "2025-02-01",
                "extracted_payload": {
                    "ticker": "AMZN",
                    "filing_type": "10-K",
                    "filing_date": "2025-02-01",
                    "financial_metrics": {"revenue": {"numeric_value": 637959}},
                },
                "signals_payload": {
                    "company": "AMZN",
                    "metrics": {
                        "operating_margin": 0.109,
                        "net_margin": 0.094,
                        "capex_ratio": 0.147,
                        "revenue_growth": 0.11,
                        "operating_income_growth": 0.86,
                        "net_income_growth": 0.95,
                    },
                    "signals": [
                        {"signal": "AI Platform Scale"},
                    ],
                },
                "insight_payload": {"takeaways": [{"text": "AMZN takeaway"}]},
            },
            {
                "ticker": "GOOGL",
                "filing_date": "2025-02-05",
                "extracted_payload": {
                    "ticker": "GOOGL",
                    "filing_type": "10-K",
                    "filing_date": "2025-02-05",
                    "financial_metrics": {"revenue": {"numeric_value": 350018}},
                },
                "signals_payload": {
                    "company": "GOOGL",
                    "metrics": {
                        "operating_margin": 0.321,
                        "net_margin": 0.289,
                        "capex_ratio": 0.111,
                        "revenue_growth": 0.132,
                        "operating_income_growth": 0.17,
                        "net_income_growth": 0.21,
                    },
                    "signals": [
                        {"signal": "AI Platform Scale"},
                    ],
                },
                "insight_payload": {"takeaways": [{"text": "GOOGL takeaway"}]},
            },
            {
                "ticker": "META",
                "filing_date": "2025-01-30",
                "extracted_payload": {
                    "ticker": "META",
                    "filing_type": "10-K",
                    "filing_date": "2025-01-30",
                    "financial_metrics": {"revenue": {"numeric_value": 164501}},
                },
                "signals_payload": {
                    "company": "META",
                    "metrics": {
                        "operating_margin": 0.417,
                        "net_margin": 0.348,
                        "capex_ratio": 0.213,
                        "revenue_growth": 0.22,
                        "operating_income_growth": 0.484,
                        "net_income_growth": 0.595,
                    },
                    "signals": [
                        {"signal": "AI Infrastructure Builder"},
                    ],
                },
                "insight_payload": {"takeaways": [{"text": "META takeaway"}]},
            },
        ]

    def test_export_industry_report_writes_markdown(self) -> None:
        comparison = build_multi_company_comparison(self._multi_company_payloads())
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        output_path = export_industry_intelligence_report_markdown(
            comparison,
            output_dir=self.OUTPUT_DIR,
        )
        markdown_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_path.name, "AI_industry_intelligence_2025.md")
        self.assertIn("# AI Industry Intelligence Report", markdown_text)
        self.assertIn("## Industry Scale", markdown_text)
        self.assertIn("## Profitability Leaders", markdown_text)
        self.assertIn("## Growth Leaders", markdown_text)
        self.assertIn("## Infrastructure Builders", markdown_text)
        self.assertIn("## AI Hardware Platforms", markdown_text)
        self.assertIn("## Data Quality Notes", markdown_text)
        self.assertIn("## Strategic Observations", markdown_text)
        self.assertIn("1. AMZN: 637,959", markdown_text)
        self.assertIn("1. NVDA: 62.4%", markdown_text)
        self.assertIn("1. NVDA: 114.2%", markdown_text)
        self.assertIn(
            "- Companies investing heavily in AI infrastructure: MSFT, META",
            markdown_text,
        )
        self.assertIn(
            "- Companies benefiting from AI hardware demand: NVDA",
            markdown_text,
        )
        self.assertIn(
            "AMZN anchors the industry revenue base among the selected companies.",
            markdown_text,
        )

        output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
