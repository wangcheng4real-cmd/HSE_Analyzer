import unittest
from unittest.mock import patch

import pandas as pd

from app.core.brake.brake_data_loader import BrakeDataLoader


class BrakeDataLoaderTests(unittest.TestCase):
    def setUp(self):
        self.loader = BrakeDataLoader()

    def test_field_aliases_are_normalized(self):
        source = pd.DataFrame({
            "编号": ["LFZG001"],
            "责任承包商": ["单位甲"],
            "发出日期（审批通过时间）": ["2026-01-01"]
        })
        result = self.loader._normalize_columns(source, "整改通知")
        self.assertIn("预警编号", result.columns)
        self.assertIn("责任单位", result.columns)
        self.assertIn("发出日期", result.columns)

    def test_unit_source_is_selected_by_brake_type(self):
        source = pd.DataFrame({
            "责任单位": ["停工单位"],
            "责任承包商": ["承包商"],
            "被约谈方": ["约谈单位"],
            "发出日期": ["2026-01-01"],
            "发出时间": ["2026-01-02"],
        })
        expected = {
            "停工令": "停工单位",
            "管理约谈": "约谈单位",
            "挂牌督办": "承包商",
            "通报批评": "承包商",
            "整改通知": "承包商",
        }
        for brake_type, unit in expected.items():
            with self.subTest(brake_type=brake_type):
                result = self.loader._normalize_columns(source, brake_type)
                self.assertEqual(result.loc[0, "责任单位"], unit)

    def test_missing_type_specific_unit_field_raises(self):
        source = pd.DataFrame({"责任单位": ["单位甲"]})
        with self.assertRaisesRegex(ValueError, "管理约谈.*被约谈方"):
            self.loader._normalize_columns(source, "管理约谈")

    def test_management_interview_units_are_grouped(self):
        source = pd.DataFrame({
            "被约谈方": [
                "中核二三（水电运维）",
                "中电建核电/项目经理部/郭念全项目管理",
                "中建三局 (BOP)",
                "山东电建三公司",
            ],
            "发出时间": ["2026-01-01"] * 4,
        })
        result = self.loader._normalize_columns(source, "管理约谈")
        self.assertEqual(
            result["责任单位"].tolist(),
            ["中核二三", "中电建核电", "中建三局", "山东电建三公司"]
        )

    def test_date_source_is_selected_by_brake_type(self):
        source = pd.DataFrame({
            "责任单位": ["停工单位"],
            "责任承包商": ["承包商"],
            "被约谈方": ["约谈单位"],
            "发出日期": ["2026-01-01"],
            "发出时间": ["2026-02-02"],
        })
        interview = self.loader._normalize_columns(source, "管理约谈")
        rectification = self.loader._normalize_columns(source, "整改通知")
        self.assertEqual(interview.loc[0, "发出日期"], "2026-02-02")
        self.assertEqual(rectification.loc[0, "发出日期"], "2026-01-01")

    def test_type_detection_from_id_prefix(self):
        preview = pd.DataFrame({"编号": ["LFZG001"]})
        result = self.loader._detect_type("file.xlsx", "Sheet1", preview.columns, preview)
        self.assertEqual(result, "整改通知")

    def test_unrecognized_type_raises(self):
        preview = pd.DataFrame({"编号": ["UNKNOWN"]})
        with self.assertRaisesRegex(ValueError, "无法自动识别"):
            self.loader._detect_type("file.xlsx", "Sheet1", preview.columns, preview)

    def test_missing_normalized_id_raises(self):
        item = {"path": "fake.xlsx", "name": "fake.xlsx"}
        metadata = {"sheet_name": "Sheet1", "header_row": 0, "预警刹车类型": "整改通知"}
        with patch.object(self.loader, "inspect_file", return_value=metadata), \
             patch("app.core.brake.brake_data_loader.pd.read_excel", return_value=pd.DataFrame({
                 "主题": ["x"], "责任承包商": ["单位甲"],
                 "发出日期": ["2026-01-01"]
             })):
            with self.assertRaisesRegex(ValueError, "预警编号"):
                self.loader.read_file(item)


if __name__ == "__main__":
    unittest.main()
