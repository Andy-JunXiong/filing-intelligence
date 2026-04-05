import json
import unittest
from pathlib import Path

from app.intelligence.comparison_engine import build_multi_company_comparison
from app.intelligence.visualization_engine import (
    build_visualization_datasets,
    export_visual_intelligence_markdown,
    export_visualization_datasets,
)


class VisualizationEngineTests(unittest.TestCase):
    OUTPUT_DIR = Path("test_tmp") / "visualizations"

    def _multi_company_payloads(self) -> list[dict[str, object]]:
        return [
            {
                "ticker": "MSFT",
                "filing_date": "2025-07-30",
                "extracted_payload": {
                    "ticker": "MSFT",
                    "filing_type": "10-K",
                    "filing_date": "2025-07-30",
                    "financial_metrics": {
                        "revenue": {
                            "numeric_value": 281724,
                            "unit": "million_usd",
                            "source_keyword": "total revenue",
                            "source_snippet": "Total revenue 281,724 245,122",
                            "section": "financials",
                            "raw_match": "281,724",
                        }
                    },
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
        ]

    def test_build_visualization_datasets_returns_expected_points(self) -> None:
        comparison = build_multi_company_comparison(self._multi_company_payloads())
        datasets = build_visualization_datasets(comparison)

        self.assertEqual(set(datasets.keys()), {"profit_pool_scatter", "growth_vs_profit", "capex_vs_scale"})
        self.assertEqual(datasets["profit_pool_scatter"]["x_metric"], "revenue")
        self.assertEqual(datasets["profit_pool_scatter"]["y_metric"], "operating_margin")
        self.assertEqual(datasets["profit_pool_scatter"]["point_count"], 3)
        msft_point = next(
            point for point in datasets["capex_vs_scale"]["points"] if point["company"] == "MSFT"
        )
        self.assertEqual(msft_point["x"], 281724)
        self.assertEqual(msft_point["y"], 0.229)
        self.assertEqual(msft_point["roles"]["infrastructure_builder"], True)
        self.assertIn("quality", msft_point)
        self.assertIn("metrics", msft_point)
        self.assertIn("takeaways", msft_point)
        self.assertIn("evidence", msft_point)
        self.assertEqual(msft_point["comparable"], True)

    def test_export_visualization_outputs_write_files(self) -> None:
        comparison = build_multi_company_comparison(self._multi_company_payloads())
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        dataset_paths = export_visualization_datasets(comparison, output_dir=self.OUTPUT_DIR)
        markdown_path = export_visual_intelligence_markdown(comparison, output_dir=self.OUTPUT_DIR)

        self.assertEqual(set(dataset_paths.keys()), {"profit_pool_scatter", "growth_vs_profit", "capex_vs_scale"})
        self.assertEqual(dataset_paths["profit_pool_scatter"].name, "profit_pool_scatter.json")
        self.assertEqual(markdown_path.name, "AI_visual_intelligence_2025.md")

        dataset_payload = json.loads(dataset_paths["growth_vs_profit"].read_text(encoding="utf-8"))
        markdown_text = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(dataset_payload["x_metric"], "revenue_growth")
        self.assertEqual(dataset_payload["y_metric"], "operating_margin")
        self.assertIn("## Profit Pool Map", markdown_text)
        self.assertIn("## Growth vs Profit", markdown_text)
        self.assertIn("## Infrastructure Investment Map", markdown_text)
        self.assertIn("## AI Ecosystem Structure", markdown_text)
        self.assertIn("profit_pool_scatter.json", markdown_text)
        self.assertIn("growth_vs_profit.json", markdown_text)
        self.assertIn("capex_vs_scale.json", markdown_text)

        for output_path in dataset_paths.values():
            output_path.unlink(missing_ok=True)
        markdown_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
