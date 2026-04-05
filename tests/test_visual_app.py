import json
import unittest
from pathlib import Path

import app_visual_intelligence as visual_app


class VisualAppTests(unittest.TestCase):
    OUTPUT_DIR = Path("test_tmp") / "visual_app"

    def test_role_label_prefers_multi_role_when_multiple_flags_are_true(self) -> None:
        role = visual_app._role_label(
            {
                "roles": {
                    "infrastructure_builder": True,
                    "ai_hardware_platform": False,
                    "ai_platform_scale": True,
                }
            }
        )

        self.assertEqual(role, "Multi-Role")

    def test_load_visualization_dataset_reads_json_file(self) -> None:
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        dataset_path = self.OUTPUT_DIR / "profit_pool_scatter.json"
        dataset_path.write_text(
            json.dumps({"dataset": "profit_pool_scatter", "points": [{"company": "MSFT"}]}),
            encoding="utf-8",
        )

        original_dir = visual_app.VISUALIZATION_DIR
        visual_app.VISUALIZATION_DIR = self.OUTPUT_DIR
        try:
            payload = visual_app.load_visualization_dataset("profit_pool_scatter.json")
        finally:
            visual_app.VISUALIZATION_DIR = original_dir

        self.assertEqual(payload["dataset"], "profit_pool_scatter")
        self.assertEqual(payload["points"][0]["company"], "MSFT")
        dataset_path.unlink(missing_ok=True)

    def test_filter_points_applies_company_role_and_confidence_filters(self) -> None:
        points = [
            {
                "company": "MSFT",
                "comparable": True,
                "roles": {
                    "infrastructure_builder": True,
                    "ai_hardware_platform": False,
                    "ai_platform_scale": False,
                },
                "quality": {"confidence": "high", "warnings": []},
            },
            {
                "company": "NVDA",
                "comparable": False,
                "roles": {
                    "infrastructure_builder": False,
                    "ai_hardware_platform": True,
                    "ai_platform_scale": False,
                },
                "quality": {"confidence": "medium", "warnings": ["sample"]},
            },
        ]

        filtered_points = visual_app._filter_points(
            points,
            selected_companies=["NVDA"],
            selected_roles=["AI Hardware Platform"],
            confidence_levels=["medium"],
        )

        self.assertEqual(len(filtered_points), 1)
        self.assertEqual(filtered_points[0]["company"], "NVDA")

    def test_filter_points_can_hide_non_comparable_points(self) -> None:
        points = [
            {"company": "MSFT", "comparable": True, "roles": {}, "quality": {"confidence": "high"}},
            {"company": "NVDA", "comparable": False, "roles": {}, "quality": {"confidence": "high"}},
        ]

        filtered_points = visual_app._filter_points(points, only_comparable=True)

        self.assertEqual(len(filtered_points), 1)
        self.assertEqual(filtered_points[0]["company"], "MSFT")

    def test_ecosystem_table_rows_include_confidence_and_roles(self) -> None:
        dataset_payloads = {
            "Profit Pool Map": {
                "points": [
                    {
                        "company": "MSFT",
                        "roles": {
                            "infrastructure_builder": True,
                            "ai_hardware_platform": False,
                            "ai_platform_scale": True,
                        },
                        "quality": {"confidence": "high", "warnings": []},
                    }
                ]
            }
        }

        rows = visual_app._ecosystem_table_rows(dataset_payloads)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Company"], "MSFT")
        self.assertEqual(rows[0]["Infrastructure Builder"], True)
        self.assertEqual(rows[0]["AI Platform Scale"], True)
        self.assertEqual(rows[0]["Confidence"], "high")

    def test_filter_points_can_show_only_warning_cases(self) -> None:
        points = [
            {
                "company": "MSFT",
                "comparable": True,
                "roles": {},
                "quality": {"confidence": "high", "warnings": []},
            },
            {
                "company": "NVDA",
                "comparable": True,
                "roles": {},
                "quality": {"confidence": "medium", "warnings": ["sample warning"]},
            },
        ]

        filtered_points = visual_app._filter_points(points, only_warnings=True)

        self.assertEqual(len(filtered_points), 1)
        self.assertEqual(filtered_points[0]["company"], "NVDA")

    def test_filtered_points_export_helpers_include_core_fields(self) -> None:
        points = [
            {
                "company": "MSFT",
                "comparable": True,
                "x": 281724,
                "y": 0.456,
                "revenue": 281724,
                "signals": ["AI Infrastructure Builder"],
                "roles": {
                    "infrastructure_builder": True,
                    "ai_hardware_platform": False,
                    "ai_platform_scale": False,
                },
                "quality": {"confidence": "high", "warnings": []},
            }
        ]

        json_text = visual_app._filtered_points_json(points)
        csv_text = visual_app._filtered_points_csv(points)

        self.assertIn('"company": "MSFT"', json_text)
        self.assertIn("company,role,confidence,warnings,revenue,x,y,signals,comparable", csv_text)
        self.assertIn("MSFT,Infrastructure Builder,high,None,281724,281724,0.456,AI Infrastructure Builder,True", csv_text)

    def test_evidence_preview_rows_build_from_point_evidence(self) -> None:
        point = {
            "evidence": {
                "revenue": {
                    "source_keyword": "total revenue",
                    "source_snippet": "Total revenue 281,724 245,122",
                },
                "operating_income": {
                    "source_keyword": "operating income",
                    "source_snippet": "Operating income 128,528 109,433",
                },
            }
        }

        rows = visual_app._evidence_preview_rows(point)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Metric"], "revenue")
        self.assertEqual(rows[0]["Keyword"], "total revenue")
        self.assertIn("Total revenue", rows[0]["Snippet"])

    def test_evidence_drilldown_items_include_full_context(self) -> None:
        point = {
            "quality": {"confidence": "medium", "warnings": ["sample warning"]},
            "evidence": {
                "revenue": {
                    "numeric_value": 281724,
                    "unit": "million_usd",
                    "section": "financials",
                    "source_keyword": "total revenue",
                    "source_snippet": "Total revenue 281,724 245,122",
                    "raw_match": "281,724",
                }
            },
        }

        items = visual_app._evidence_drilldown_items(point)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["metric_name"], "revenue")
        self.assertEqual(items[0]["extracted_value"], "281,724 (million_usd)")
        self.assertEqual(items[0]["confidence"], "medium")
        self.assertEqual(items[0]["warnings"], "sample warning")
        self.assertEqual(items[0]["section"], "financials")
        self.assertEqual(items[0]["source_keyword"], "total revenue")
        self.assertEqual(items[0]["raw_match"], "281,724")


if __name__ == "__main__":
    unittest.main()
