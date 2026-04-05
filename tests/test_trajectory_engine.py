import unittest
from pathlib import Path

from app.intelligence.trajectory_engine import (
    build_multi_year_trajectory,
    export_multi_year_trajectory_markdown,
)


class TrajectoryEngineTests(unittest.TestCase):
    OUTPUT_DIR = Path("test_tmp") / "trajectory_engine"

    def _yearly_payloads(self) -> list[dict[str, object]]:
        return [
            {
                "filing_date": "2023-01-29",
                "extracted_payload": {
                    "ticker": "NVDA",
                    "financial_metrics": {
                        "revenue": {"numeric_value": 26974},
                    },
                },
                "signals_payload": {
                    "metrics": {
                        "operating_margin": 0.163,
                        "net_margin": 0.161,
                        "capex_ratio": 0.04,
                        "revenue_growth": -0.21,
                    }
                },
            },
            {
                "filing_date": "2024-01-28",
                "extracted_payload": {
                    "ticker": "NVDA",
                    "financial_metrics": {
                        "revenue": {"numeric_value": 60922},
                    },
                },
                "signals_payload": {
                    "metrics": {
                        "operating_margin": 0.541,
                        "net_margin": 0.488,
                        "capex_ratio": 0.056,
                        "revenue_growth": 1.259,
                    }
                },
            },
            {
                "filing_date": "2025-02-26",
                "extracted_payload": {
                    "ticker": "NVDA",
                    "financial_metrics": {
                        "revenue": {"numeric_value": 130497},
                    },
                },
                "signals_payload": {
                    "metrics": {
                        "operating_margin": 0.624,
                        "net_margin": 0.558,
                        "capex_ratio": 0.025,
                        "revenue_growth": 1.142,
                    }
                },
            },
        ]

    def test_build_multi_year_trajectory_creates_metric_series(self) -> None:
        trajectory = build_multi_year_trajectory(
            company="NVDA",
            filing_type="10-K",
            yearly_payloads=self._yearly_payloads(),
        )

        self.assertEqual(trajectory["filing_years"], ["2023", "2024", "2025"])
        self.assertEqual(trajectory["metrics"]["revenue"][0]["value"], 26974)
        self.assertEqual(trajectory["metrics"]["operating_margin"][-1]["value"], 0.624)

    def test_build_multi_year_trajectory_generates_insights(self) -> None:
        trajectory = build_multi_year_trajectory(
            company="NVDA",
            filing_type="10-K",
            yearly_payloads=self._yearly_payloads(),
        )

        self.assertEqual(
            trajectory["insights"]["revenue_trajectory"],
            "NVDA demonstrates sustained revenue acceleration across the past three filings.",
        )
        self.assertEqual(
            trajectory["insights"]["margin_expansion"],
            "NVDA shows significant margin expansion driven by AI demand.",
        )
        self.assertEqual(
            trajectory["insights"]["capex_cycle"],
            "NVDA is moderating its capex cycle relative to revenue.",
        )

    def test_export_multi_year_trajectory_markdown_writes_report(self) -> None:
        trajectory = build_multi_year_trajectory(
            company="NVDA",
            filing_type="10-K",
            yearly_payloads=self._yearly_payloads(),
        )
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = export_multi_year_trajectory_markdown(
            trajectory,
            output_dir=self.OUTPUT_DIR,
        )
        markdown_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_path.name, "NVDA_3yr_analysis.md")
        self.assertIn("# Multi-Year Financial Trajectory", markdown_text)
        self.assertIn("## Revenue Trajectory", markdown_text)
        self.assertIn("NVDA demonstrates sustained revenue acceleration across the past three filings.", markdown_text)
        output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
