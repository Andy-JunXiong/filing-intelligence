import unittest

from app.exporters import build_extracted_metrics_payload
from app.quality import assess_extracted_payload_quality, build_data_quality_notes, merge_company_quality
from app.schemas import ExtractedMetric, FilingMetadata
from signals.financial_signals import build_financial_signals


class QualityLayerTests(unittest.TestCase):
    def _metadata(self) -> FilingMetadata:
        return FilingMetadata(
            company="Microsoft",
            ticker="MSFT",
            filing_type="10-K",
            filing_date="2025-07-30",
            source_url="local",
        )

    def _metrics(self) -> dict[str, ExtractedMetric | None]:
        return {
            "revenue": ExtractedMetric(
                value=281724,
                numeric_value=281724,
                raw_value="281,724",
                unit="million_usd",
                source_keyword="total revenue",
                source_snippet="Total revenue 281,724 245,122",
                section="financials",
                raw_match="281,724",
            ),
            "previous_revenue": ExtractedMetric(
                value=245122,
                numeric_value=245122,
                raw_value="245,122",
                unit="million_usd",
                source_keyword="total revenue",
                source_snippet="Total revenue 281,724 245,122",
                section="financials",
                raw_match="245,122",
            ),
            "operating_income": ExtractedMetric(
                value=128528,
                numeric_value=128528,
                raw_value="128,528",
                unit="million_usd",
                source_keyword="operating income",
                source_snippet="Operating income 128,528 109,433",
                section="financials",
                raw_match="128,528",
            ),
            "previous_operating_income": ExtractedMetric(
                value=109433,
                numeric_value=109433,
                raw_value="109,433",
                unit="million_usd",
                source_keyword="operating income",
                source_snippet="Operating income 128,528 109,433",
                section="financials",
                raw_match="109,433",
            ),
            "net_income": ExtractedMetric(
                value=101832,
                numeric_value=101832,
                raw_value="101,832",
                unit="million_usd",
                source_keyword="net income",
                source_snippet="Net income 101,832 88,136",
                section="financials",
                raw_match="101,832",
            ),
            "previous_net_income": ExtractedMetric(
                value=88136,
                numeric_value=88136,
                raw_value="88,136",
                unit="million_usd",
                source_keyword="net income",
                source_snippet="Net income 101,832 88,136",
                section="financials",
                raw_match="88,136",
            ),
            "capex": ExtractedMetric(
                value=64551,
                numeric_value=64551,
                raw_value="64,551",
                unit="million_usd",
                source_keyword="additions to property and equipment",
                source_snippet="Additions to property and equipment 64,551",
                section="financials",
                raw_match="64,551",
            ),
        }

    def test_extracted_payload_preserves_evidence_fields_and_high_confidence(self) -> None:
        payload = build_extracted_metrics_payload(self._metadata(), self._metrics())

        revenue = payload["financial_metrics"]["revenue"]
        self.assertEqual(revenue["source_keyword"], "total revenue")
        self.assertEqual(revenue["section"], "financials")
        self.assertEqual(revenue["raw_match"], "281,724")
        self.assertEqual(revenue["unit"], "million_usd")
        self.assertIn("Total revenue 281,724", revenue["source_snippet"])
        self.assertEqual(payload["quality"]["confidence"], "high")
        self.assertTrue(payload["quality"]["evidence"]["revenue"]["has_full_evidence"])
        self.assertTrue(payload["quality"]["evidence"]["previous_revenue"]["has_full_evidence"])

    def test_extracted_quality_warns_when_revenue_is_not_positive(self) -> None:
        payload = {
            "ticker": "TEST",
            "financial_metrics": {
                "revenue": {"numeric_value": 0},
                "operating_income": {"numeric_value": 10},
                "net_income": {"numeric_value": 8},
                "capex": {"numeric_value": 2},
            },
        }

        quality = assess_extracted_payload_quality(payload, company="TEST")

        self.assertEqual(quality["confidence"], "low")
        self.assertIn("TEST revenue must be greater than zero.", quality["warnings"])

    def test_merge_company_quality_collects_growth_caution_notes(self) -> None:
        extracted_payload = build_extracted_metrics_payload(self._metadata(), self._metrics())
        extracted_payload["financial_metrics"]["previous_revenue"] = None
        extracted_payload["quality"] = assess_extracted_payload_quality(extracted_payload, company="MSFT")

        signals_payload = build_financial_signals(extracted_payload)
        merged_quality = merge_company_quality("MSFT", extracted_payload, signals_payload)
        notes = build_data_quality_notes({"MSFT": merged_quality})

        self.assertEqual(merged_quality["confidence"], "medium")
        self.assertTrue(any("missing prior-year evidence" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
