import unittest

import pandas as pd

from app.core.hazard.hazard_config import HazardConfig
from app.core.hazard.hazard_preprocessor import HazardPreprocessor


class HazardPreprocessorTests(unittest.TestCase):
    def setUp(self):
        self.cfg = HazardConfig()
        self.preprocessor = HazardPreprocessor(self.cfg)

    def test_normalizes_column_names_without_mutating_source(self):
        source = pd.DataFrame({" 责任单位 ": ["单位甲"]})
        result = self.preprocessor.normalize_columns(source)
        self.assertIn("责任单位", result.columns)
        self.assertIn(" 责任单位 ", source.columns)

    def test_returns_missing_columns(self):
        missing = self.preprocessor.require_columns(pd.DataFrame({"A": [1]}), ["A", "B"])
        self.assertEqual(missing, ["B"])

    def test_cleans_null_blank_and_whitespace_text(self):
        source = pd.DataFrame({"责任单位": [" 单位甲 ", "", "   ", None]})
        result = self.preprocessor.clean_text_column(source, "责任单位")
        self.assertEqual(result["责任单位"].tolist(), ["单位甲"])

    def test_filters_contractor_flow_after_trimming(self):
        source = pd.DataFrame({"流程类型": [" 工程公司录入承包商 ", "其他流程", None]})
        result = self.preprocessor.filter_contractor_flow(source)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["流程类型"].iloc[0], "工程公司录入承包商")

    def test_extracts_main_area(self):
        source = pd.DataFrame({"区域": [" 厂房A/一层 ", "厂房B", ""]})
        result = self.preprocessor.with_main_area(source)
        self.assertEqual(result["区域大类"].tolist(), ["厂房A", "厂房B"])

    def test_category_path_and_second_category_have_distinct_meaning(self):
        source = pd.DataFrame({"隐患分类": ["施工/用电/临电", "施工"]})
        path_result = self.preprocessor.with_category_path2(source)
        second_result = self.preprocessor.with_second_category(source)
        self.assertEqual(path_result["隐患类别二级路径"].tolist(), ["施工/用电", "施工"])
        self.assertEqual(second_result["隐患第二级分类"].tolist(), ["用电"])


if __name__ == "__main__":
    unittest.main()
