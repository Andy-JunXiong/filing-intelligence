import tempfile
import unittest
from pathlib import Path

from app.intelligence.insight_generator import build_structured_insight, export_structured_insight


class InsightGeneratorTests(unittest.TestCase):
    def _extracted_payload(self) -> dict[str, object]:
        return {
            "ticker": "MSFT",
            "company": "Microsoft",
            "filing_type": "10-K",
            "filing_date": "2025-07-30",
            "financial_metrics": {},
        }

    def test_high_capex_ratio_generates_infrastructure_takeaway(self) -> None:
        signals_payload = {
            "company": "MSFT",
            "filing_type": "10-K",
            "filing_date": "2025-07-30",
            "metrics": {"operating_margin": 0.20, "net_margin": 0.10, "capex_ratio": 0.229},
            "signals": [{"type": "capex_intensity", "value": 0.229, "signal": "High infrastructure investment"}],
        }

        insight = build_structured_insight(self._extracted_payload(), signals_payload)

        self.assertIn(
            "The company is investing heavily in infrastructure relative to revenue.",
            [takeaway["text"] for takeaway in insight["takeaways"]],
        )
        self.assertEqual(insight["takeaways"][0]["evidence"]["capex_ratio"], 0.229)

    def test_high_operating_margin_generates_profitability_takeaway(self) -> None:
        signals_payload = {
            "company": "MSFT",
            "filing_type": "10-K",
            "filing_date": "2025-07-30",
            "metrics": {"operating_margin": 0.456, "net_margin": 0.20, "capex_ratio": 0.10},
            "signals": [{"type": "operating_margin", "value": 0.456, "signal": "High profitability"}],
        }

        insight = build_structured_insight(self._extracted_payload(), signals_payload)

        self.assertIn(
            "The company maintains strong operating profitability.",
            [takeaway["text"] for takeaway in insight["takeaways"]],
        )
        self.assertEqual(insight["takeaways"][0]["evidence"]["operating_margin"], 0.456)

    def test_high_capex_and_high_profitability_generate_combined_takeaway(self) -> None:
        signals_payload = {
            "company": "MSFT",
            "filing_type": "10-K",
            "filing_date": "2025-07-30",
            "metrics": {"operating_margin": 0.456, "net_margin": 0.361, "capex_ratio": 0.229},
            "signals": [
                {"type": "capex_intensity", "value": 0.229, "signal": "High infrastructure investment"},
                {"type": "operating_margin", "value": 0.456, "signal": "High profitability"},
            ],
        }

        insight = build_structured_insight(self._extracted_payload(), signals_payload)

        self.assertIn(
            "The company combines strong profitability with elevated infrastructure investment, suggesting capacity to fund long-term AI expansion.",
            [takeaway["text"] for takeaway in insight["takeaways"]],
        )
        self.assertEqual(
            insight["takeaways"][0]["evidence"]["signals"],
            ["High infrastructure investment", "High profitability"],
        )

    def test_export_structured_insight_writes_markdown(self) -> None:
        insight_payload = {
            "company": "MSFT",
            "filing_type": "10-K",
            "filing_date": "2025-07-30",
            "metrics_summary": {"operating_margin": 0.456, "net_margin": 0.361, "capex_ratio": 0.229},
            "signals_summary": ["High infrastructure investment", "High profitability"],
            "takeaways": [
                {
                    "text": "The company maintains strong operating profitability.",
                    "evidence": {"operating_margin": 0.456, "signal": "High profitability"},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = export_structured_insight(insight_payload, output_dir=Path(temp_dir))
            content = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_path.name, "MSFT_10-K_2025.md")
        self.assertIn("## Takeaways", content)
        self.assertIn("The company maintains strong operating profitability.", content)
        self.assertIn("Evidence: operating_margin=0.456, signal=High profitability", content)


if __name__ == "__main__":
    unittest.main()
