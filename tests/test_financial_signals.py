import json
import logging
import unittest
from pathlib import Path

from app.exporters import build_extracted_metrics_payload
from app.extraction.financial_extractor import extract_financial_metrics
from app.parsing.filing_parser import parse_filing
from app.schemas import FilingMetadata, RawFiling
from signals.financial_signals import build_financial_signals, export_financial_signals


class FinancialSignalsTests(unittest.TestCase):
    OUTPUT_DIR = Path("test_tmp") / "financial_signals"

    def _build_extracted_payload(self) -> dict[str, object]:
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
                <p>Total revenue 281,724 245,122</p>
                <p>Operating income 128,528 109,433</p>
                <p>Net income 101,832 88,136</p>
                <p>Additions to property and equipment 64,551</p>
                """,
                storage_path="",
            )
        )
        metrics = extract_financial_metrics(parsed_filing)
        return build_extracted_metrics_payload(parsed_filing.metadata, metrics)

    def test_build_financial_signals_calculates_ratios_and_signals(self) -> None:
        extracted_payload = self._build_extracted_payload()

        signals_payload = build_financial_signals(extracted_payload)

        self.assertEqual(signals_payload["company"], "MSFT")
        self.assertEqual(
            signals_payload["metrics"],
            {
                "operating_margin": 0.456,
                "net_margin": 0.361,
                "capex_ratio": 0.229,
                "revenue_growth": 0.149,
                "operating_income_growth": 0.174,
                "net_income_growth": 0.155,
            },
        )
        self.assertEqual(
            signals_payload["signals"],
            [
                {
                    "type": "capex_intensity",
                    "value": 0.229,
                    "signal": "High infrastructure investment",
                },
                {
                    "type": "operating_margin",
                    "value": 0.456,
                    "signal": "High profitability",
                },
                {
                    "type": "ai_infrastructure_builder",
                    "value": 0.229,
                    "signal": "AI Infrastructure Builder",
                },
                {
                    "type": "ai_platform_scale",
                    "value": 0.229,
                    "signal": "AI Platform Scale",
                },
            ],
        )
        self.assertEqual(signals_payload["warnings"], [])
        self.assertEqual(signals_payload["quality"]["confidence"], "high")

    def test_export_financial_signals_writes_json_file(self) -> None:
        signals_payload = build_financial_signals(self._build_extracted_payload())
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = export_financial_signals(signals_payload, output_dir=self.OUTPUT_DIR)
        payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(output_path.name, "MSFT_10-K_2025.json")
        self.assertEqual(payload["company"], "MSFT")
        self.assertEqual(payload["metrics"]["capex_ratio"], 0.229)
        self.assertEqual(payload["signals"][0]["signal"], "High infrastructure investment")
        output_path.unlink(missing_ok=True)

    def test_build_financial_signals_uses_absolute_capex_for_ratio(self) -> None:
        extracted_payload = {
            "ticker": "NVDA",
            "filing_type": "10-K",
            "filing_date": "2025-02-26",
            "financial_metrics": {
                "revenue": {"numeric_value": 130497},
                "previous_revenue": {"numeric_value": 60922},
                "operating_income": {"numeric_value": 81453},
                "previous_operating_income": {"numeric_value": 32972},
                "net_income": {"numeric_value": 72880},
                "previous_net_income": {"numeric_value": 29760},
                "capex": {"numeric_value": -3236},
            },
        }

        signals_payload = build_financial_signals(extracted_payload)

        self.assertEqual(signals_payload["metrics"]["capex_ratio"], 0.025)
        self.assertEqual(signals_payload["metrics"]["revenue_growth"], 1.142)

    def test_build_financial_signals_discards_implausible_ratios_and_logs_warning(self) -> None:
        extracted_payload = {
            "ticker": "GOOGL",
            "filing_type": "10-K",
            "filing_date": "2025-02-05",
            "financial_metrics": {
                "revenue": {"numeric_value": 8876},
                "operating_income": {"numeric_value": 74842},
                "net_income": {"numeric_value": 59972},
                "capex": {"numeric_value": 31485},
            },
        }

        with self.assertLogs("signals.financial_signals", level=logging.WARNING) as captured:
            signals_payload = build_financial_signals(extracted_payload)

        self.assertIsNone(signals_payload["metrics"]["operating_margin"])
        self.assertIsNone(signals_payload["metrics"]["net_margin"])
        self.assertIsNone(signals_payload["metrics"]["capex_ratio"])
        self.assertEqual(signals_payload["quality"]["confidence"], "low")
        self.assertTrue(any("operating_margin=" in warning for warning in signals_payload["warnings"]))
        self.assertTrue(any("Discarding implausible operating_margin" in message for message in captured.output))
        self.assertTrue(any("Discarding implausible capex_ratio" in message for message in captured.output))

    def test_build_financial_signals_handles_missing_previous_values(self) -> None:
        extracted_payload = {
            "ticker": "META",
            "filing_type": "10-K",
            "filing_date": "2025-01-30",
            "financial_metrics": {
                "revenue": {"numeric_value": 164501},
                "operating_income": {"numeric_value": 69380},
                "net_income": {"numeric_value": 62360},
                "capex": {"numeric_value": 37256},
            },
        }

        signals_payload = build_financial_signals(extracted_payload)

        self.assertIsNone(signals_payload["metrics"]["revenue_growth"])
        self.assertIsNone(signals_payload["metrics"]["operating_income_growth"])
        self.assertIsNone(signals_payload["metrics"]["net_income_growth"])
        self.assertEqual(signals_payload["quality"]["confidence"], "medium")
        self.assertTrue(
            any("missing prior-year evidence" in note for note in signals_payload["quality"]["notes"])
        )

    def test_build_financial_signals_adds_ai_hardware_platform_signal(self) -> None:
        extracted_payload = {
            "ticker": "NVDA",
            "filing_type": "10-K",
            "filing_date": "2025-02-26",
            "financial_metrics": {
                "revenue": {"numeric_value": 130497},
                "previous_revenue": {"numeric_value": 60922},
                "operating_income": {"numeric_value": 81453},
                "previous_operating_income": {"numeric_value": 32972},
                "net_income": {"numeric_value": 72880},
                "previous_net_income": {"numeric_value": 29760},
                "capex": {"numeric_value": 3236},
            },
        }

        signals_payload = build_financial_signals(extracted_payload)
        signal_labels = [signal["signal"] for signal in signals_payload["signals"]]

        self.assertIn("AI Hardware Platform", signal_labels)
        self.assertNotIn("AI Platform Scale", signal_labels)


if __name__ == "__main__":
    unittest.main()
