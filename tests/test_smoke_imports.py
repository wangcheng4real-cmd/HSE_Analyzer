import ast
import importlib
import inspect
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))


class SmokeTests(unittest.TestCase):
    def test_core_modules_import(self):
        for module_name in (
            "app.core.analyzer",
            "app.core.hazard.hazard_data_loader",
            "app.core.hazard.hazard_analyzer",
            "app.core.brake.brake_analyzer",
            "app.core.brake.brake_data_loader",
            "app.core.brake.brake_special_trend_service",
            "app.core.risk.risk_analyzer",
            "app.core.risk.rule_repository",
        ):
            self.assertIsNotNone(importlib.import_module(module_name))

    def test_page_classes_have_one_init_definition(self):
        for relative_path, class_name in (
            ("app/ui/pages/hazard_page.py", "HazardPage"),
            ("app/ui/pages/brake_page.py", "BrakePage"),
        ):
            path = os.path.join(ROOT, *relative_path.split("/"))
            with open(path, "r", encoding="utf-8") as source:
                tree = ast.parse(source.read())
            page_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
            init_count = sum(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__init__"
                for node in page_class.body
            )
            self.assertEqual(init_count, 1, relative_path)

    def test_core_loader_interfaces(self):
        from app.core.hazard.hazard_data_loader import HazardDataLoader
        from app.core.brake.brake_data_loader import BrakeDataLoader

        self.assertIn("period_type", inspect.signature(HazardDataLoader.load).parameters)
        self.assertTrue(callable(HazardDataLoader.group_by_period))
        self.assertTrue(callable(BrakeDataLoader.load))

    def test_page_analysis_callbacks_are_inherited(self):
        from app.ui.pages.hazard_page import HazardPage
        from app.ui.pages.brake_page import BrakePage

        for callback in (
            "level_chart", "unit_chart", "area_chart", "trend_chart",
            "ab_trend_chart", "special_unit_category_ui",
            "special_area_category_ui", "special_trend_category_ui"
        ):
            self.assertTrue(callable(getattr(HazardPage, callback)))
        for callback in (
            "show_type_chart", "show_unit_top10", "show_category_chart",
            "show_overall_weekly_trend", "open_unit_trend_selection"
            , "open_special_category_selection", "open_special_trend_category_selection"
        ):
            self.assertTrue(callable(getattr(BrakePage, callback)))


if __name__ == "__main__":
    unittest.main()
