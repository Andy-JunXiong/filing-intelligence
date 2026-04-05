import json
import unittest
from pathlib import Path

from app.intelligence.comparison_engine import (
    build_company_comparison,
    build_multi_company_comparison,
    export_company_comparison,
    export_company_comparison_markdown,
    export_multi_company_comparison,
    export_multi_company_comparison_markdown,
)


class ComparisonEngineTests(unittest.TestCase):
    OUTPUT_DIR = Path("test_tmp") / "comparison_engine"

    def _payloads(
        self,
        *,
        msft_date: str = "2025-07-30",
        nvda_date: str = "2025-02-21",
        msft_capex_ratio: float | None = 0.229,
        nvda_capex_ratio: float | None = 0.025,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
        msft_extracted = {
            "ticker": "MSFT",
            "filing_type": "10-K",
            "filing_date": msft_date,
            "financial_metrics": {
                "revenue": {"numeric_value": 281724},
            },
        }
        msft_signals = {
            "company": "MSFT",
            "metrics": {
                "operating_margin": 0.456,
                "net_margin": 0.361,
                "capex_ratio": msft_capex_ratio,
                "revenue_growth": 0.149,
                "operating_income_growth": 0.175,
                "net_income_growth": 0.156,
            },
            "signals": [
                {"type": "capex_intensity", "value": 0.229, "signal": "High infrastructure investment"},
                {"type": "operating_margin", "value": 0.456, "signal": "High profitability"},
                {"type": "ai_infrastructure_builder", "value": 0.229, "signal": "AI Infrastructure Builder"},
                {"type": "ai_platform_scale", "value": 0.229, "signal": "AI Platform Scale"},
            ],
        }
        msft_insight = {"takeaways": [{"text": "MSFT takeaway"}]}

        nvda_extracted = {
            "ticker": "NVDA",
            "filing_type": "10-K",
            "filing_date": nvda_date,
            "financial_metrics": {
                "revenue": {"numeric_value": 130497},
            },
        }
        nvda_signals = {
            "company": "NVDA",
            "metrics": {
                "operating_margin": 0.624,
                "net_margin": 0.558,
                "capex_ratio": nvda_capex_ratio,
                "revenue_growth": 1.142,
                "operating_income_growth": 1.471,
                "net_income_growth": 1.449,
            },
            "signals": [
                {"type": "operating_margin", "value": 0.624, "signal": "High profitability"},
                {"type": "ai_hardware_platform", "value": 0.624, "signal": "AI Hardware Platform"},
            ],
        }
        nvda_insight = {"takeaways": [{"text": "NVDA takeaway"}]}
        return msft_extracted, msft_signals, msft_insight, nvda_extracted, nvda_signals, nvda_insight

    def _multi_company_payloads(self, *, googl_capex_ratio: float | None = 0.111, mismatched_year: bool = False) -> list[dict[str, object]]:
        googl_date = "2026-02-05" if mismatched_year else "2025-02-05"
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
                        {"signal": "High infrastructure investment"},
                        {"signal": "High profitability"},
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
                    "signals": [{"signal": "High profitability"}, {"signal": "AI Hardware Platform"}],
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
                    "signals": [{"signal": "Moderate profitability"}, {"signal": "AI Platform Scale"}],
                },
                "insight_payload": {"takeaways": [{"text": "AMZN takeaway"}]},
            },
            {
                "ticker": "GOOGL",
                "filing_date": googl_date,
                "extracted_payload": {
                    "ticker": "GOOGL",
                    "filing_type": "10-K",
                    "filing_date": googl_date,
                    "financial_metrics": {"revenue": {"numeric_value": 350018}},
                },
                "signals_payload": {
                    "company": "GOOGL",
                    "metrics": {
                        "operating_margin": 0.321,
                        "net_margin": 0.289,
                        "capex_ratio": googl_capex_ratio,
                        "revenue_growth": 0.132,
                        "operating_income_growth": 0.17,
                        "net_income_growth": 0.21,
                    },
                    "signals": [{"signal": "Disciplined infrastructure investment"}, {"signal": "AI Platform Scale"}],
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
                    "signals": [{"signal": "High infrastructure investment"}, {"signal": "AI Infrastructure Builder"}],
                },
                "insight_payload": {"takeaways": [{"text": "META takeaway"}]},
            },
        ]

    def test_build_company_comparison_compares_metrics(self) -> None:
        comparison = build_company_comparison(*self._payloads())

        self.assertEqual(comparison["metrics"]["revenue"]["higher"], "MSFT")
        self.assertEqual(comparison["metrics"]["operating_margin"]["higher"], "NVDA")
        self.assertEqual(comparison["metrics"]["capex_ratio"]["higher"], "MSFT")
        self.assertEqual(comparison["metrics"]["revenue_growth"]["higher"], "NVDA")
        self.assertEqual(comparison["comparability"]["same_filing_year"], True)
        self.assertEqual(
            comparison["ai_infrastructure_landscape"]["infrastructure_builders"],
            ["MSFT"],
        )
        self.assertEqual(
            comparison["ai_infrastructure_landscape"]["ai_hardware_platforms"],
            ["NVDA"],
        )

    def test_build_company_comparison_generates_takeaways(self) -> None:
        comparison = build_company_comparison(*self._payloads())

        self.assertEqual(
            comparison["takeaways"],
            [
                "NVDA shows the stronger operating profitability.",
                "MSFT shows higher infrastructure investment intensity relative to revenue.",
                "MSFT reports the higher revenue in the selected filing year.",
                "NVDA shows the stronger revenue growth.",
                "NVDA shows the stronger net income growth.",
            ],
        )

    def test_build_company_comparison_flags_non_comparable_fields(self) -> None:
        comparison = build_company_comparison(
            *self._payloads(msft_capex_ratio=None, nvda_capex_ratio=0.025)
        )

        self.assertIn("capex_ratio", comparison["comparability"]["non_comparable_fields"])
        self.assertIn(
            "Not fully comparable: capex_ratio.",
            comparison["takeaways"],
        )

    def test_build_company_comparison_blocks_takeaways_when_years_differ(self) -> None:
        comparison = build_company_comparison(
            *self._payloads(msft_date="2025-07-30", nvda_date="2026-02-25")
        )

        self.assertEqual(comparison["filing_year"], None)
        self.assertEqual(comparison["comparability"]["same_filing_year"], False)
        self.assertEqual(comparison["takeaways"], [])

    def test_export_company_comparison_writes_json_and_markdown(self) -> None:
        comparison = build_company_comparison(*self._payloads())
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_output_path = export_company_comparison(comparison, output_dir=self.OUTPUT_DIR)
        markdown_output_path = export_company_comparison_markdown(
            comparison,
            output_dir=self.OUTPUT_DIR,
        )
        payload = json.loads(json_output_path.read_text(encoding="utf-8"))
        markdown_text = markdown_output_path.read_text(encoding="utf-8")

        self.assertEqual(json_output_path.name, "MSFT_vs_NVDA_10-K_2025.json")
        self.assertEqual(markdown_output_path.name, "MSFT_vs_NVDA_10-K_2025.md")
        self.assertEqual(payload["companies"], ["MSFT", "NVDA"])
        self.assertIn("# Financial Comparison", markdown_text)
        self.assertIn("MSFT vs NVDA (10-K 2025)", markdown_text)
        self.assertIn("## Summary", markdown_text)
        self.assertIn("## Revenue", markdown_text)
        self.assertIn("- MSFT: 281,724", markdown_text)
        self.assertIn("- NVDA: 62.4%", markdown_text)
        self.assertIn("## Signals Comparison", markdown_text)
        self.assertIn("## AI Infrastructure Landscape", markdown_text)
        self.assertIn("- Infrastructure Builders: MSFT", markdown_text)
        self.assertIn("- AI Hardware Platforms: NVDA", markdown_text)
        self.assertIn("## Revenue Growth", markdown_text)
        self.assertIn("- NVDA: 114.2%", markdown_text)
        self.assertIn("## Final Takeaways", markdown_text)
        self.assertIn("MSFT shows higher infrastructure investment intensity relative to revenue.", markdown_text)
        json_output_path.unlink(missing_ok=True)
        markdown_output_path.unlink(missing_ok=True)

    def test_build_multi_company_comparison_generates_rankings(self) -> None:
        comparison = build_multi_company_comparison(self._multi_company_payloads())

        self.assertEqual(comparison["companies"], ["MSFT", "NVDA", "AMZN", "GOOGL", "META"])
        self.assertEqual(comparison["filing_year"], "2025")
        self.assertEqual(comparison["rankings"]["revenue"]["leader"], "AMZN")
        self.assertEqual(comparison["rankings"]["operating_margin"]["leader"], "NVDA")
        self.assertEqual(comparison["rankings"]["capex_ratio"]["leader"], "MSFT")
        self.assertEqual(comparison["rankings"]["revenue_growth"]["leader"], "NVDA")
        self.assertEqual(comparison["rankings"]["net_income_growth"]["leader"], "NVDA")
        self.assertEqual(
            comparison["ai_infrastructure_landscape"]["infrastructure_builders"],
            ["MSFT", "META"],
        )
        self.assertEqual(
            comparison["ai_infrastructure_landscape"]["ai_hardware_platforms"],
            ["NVDA"],
        )
        self.assertEqual(
            comparison["ai_infrastructure_landscape"]["ai_platform_scale_leaders"],
            ["MSFT", "AMZN", "GOOGL"],
        )
        self.assertIn(
            "NVDA demonstrates the highest operating profitability among the selected companies.",
            comparison["takeaways"],
        )
        self.assertIn(
            "NVDA demonstrates the strongest revenue growth among the selected companies.",
            comparison["takeaways"],
        )

    def test_build_multi_company_comparison_handles_missing_values(self) -> None:
        comparison = build_multi_company_comparison(
            self._multi_company_payloads(googl_capex_ratio=None)
        )

        self.assertIn("capex_ratio", comparison["comparability"]["non_comparable_fields"])
        capex_ranking = comparison["rankings"]["capex_ratio"]["ranking"]
        self.assertEqual(capex_ranking[-1]["company"], "GOOGL")
        self.assertEqual(capex_ranking[-1]["value"], None)

    def test_build_multi_company_comparison_blocks_takeaways_when_years_differ(self) -> None:
        comparison = build_multi_company_comparison(
            self._multi_company_payloads(mismatched_year=True)
        )

        self.assertEqual(comparison["filing_year"], None)
        self.assertEqual(comparison["comparability"]["same_filing_year"], False)
        self.assertEqual(comparison["takeaways"], [])

    def test_export_multi_company_comparison_writes_json_and_markdown(self) -> None:
        comparison = build_multi_company_comparison(self._multi_company_payloads())
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_output_path = export_multi_company_comparison(comparison, output_dir=self.OUTPUT_DIR)
        markdown_output_path = export_multi_company_comparison_markdown(
            comparison,
            output_dir=self.OUTPUT_DIR,
        )
        payload = json.loads(json_output_path.read_text(encoding="utf-8"))
        markdown_text = markdown_output_path.read_text(encoding="utf-8")

        self.assertEqual(json_output_path.name, "AI_sector_10-K_2025.json")
        self.assertEqual(markdown_output_path.name, "AI_sector_10-K_2025.md")
        self.assertEqual(payload["rankings"]["revenue"]["leader"], "AMZN")
        self.assertIn("# Multi-Company Financial Comparison", markdown_text)
        self.assertIn("## Revenue Ranking", markdown_text)
        self.assertIn("## Revenue Growth Ranking", markdown_text)
        self.assertIn("1. AMZN: 637,959", markdown_text)
        self.assertIn("1. NVDA: 114.2%", markdown_text)
        self.assertIn("## AI Infrastructure Landscape", markdown_text)
        self.assertIn("- Infrastructure Builders: MSFT, META", markdown_text)
        self.assertIn("- AI Hardware Platforms: NVDA", markdown_text)
        self.assertIn("- AI Platform Scale Leaders: MSFT, AMZN, GOOGL", markdown_text)
        self.assertIn("## Key Takeaways", markdown_text)
        self.assertIn(
            "NVDA demonstrates the highest operating profitability among the selected companies.",
            markdown_text,
        )
        json_output_path.unlink(missing_ok=True)
        markdown_output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
