import unittest

import pandas as pd

from app.core.hazard.hazard_config import HazardConfig
from app.core.hazard.hazard_filter import HazardFilter
from app.core.hazard.hazard_analyzer import HazardAnalyzer


class HazardServiceTests(unittest.TestCase):
    def setUp(self):
        self.cfg = HazardConfig()
        self.analyzer = HazardAnalyzer(self.cfg)
        self.df = pd.DataFrame({
            "隐患单号": ["H1", "H2", "H3", "H4"],
            "检查日期": pd.to_datetime(["2026-01-05"] * 4),
            "隐患级别": ["A", "B", "C", "A"],
            "流程类型": ["工程公司录入承包商"] * 4,
            "状态": ["完成", "进行中", "完成", "已取消"],
            "责任单位": ["单位甲", "单位甲", "单位乙", "单位乙"],
            "隐患分类": ["施工/用电", "施工/高处", "设备/机械", "施工/用电"],
            "区域": ["厂房A/一层", "厂房A/二层", "厂房B/一层", "厂房B/二层"],
            "接口队办": ["队1", "队1", "队2", "队2"],
            "责任班组": ["班组1", "班组2", "班组3", "班组4"],
            "验证状态": ["按期验证", "逾期验证", "按期验证", "按期验证"],
            "时间周期": ["2026-01-05 至 2026-01-11"] * 4,
            "周期开始日期": pd.to_datetime(["2026-01-05"] * 4),
        })

    def test_common_status_filter(self):
        result = HazardFilter(self.cfg).apply(self.df)
        self.assertEqual(len(result), 3)
        self.assertNotIn("已取消", result["状态"].tolist())

    def test_representative_overall_services(self):
        for result in (
            self.analyzer.level_analysis(self.df),
            self.analyzer.unit_analysis(self.df),
            self.analyzer.category_main_analysis(self.df),
            self.analyzer.area_analysis(self.df),
            self.analyzer.ab_level_analysis(self.df),
        ):
            self.assertIsNotNone(result)
            self.assertGreater(len(result), 0)

    def test_representative_trends(self):
        groups = [self.df.copy()]
        self.assertEqual(len(self.analyzer.trend_analysis(groups)), 1)
        self.assertEqual(len(self.analyzer.unit_trend_analysis(groups, "单位甲")), 1)
        self.assertEqual(len(self.analyzer.area_trend_analysis(groups, "厂房A")), 1)

        typed = self.analyzer.period_trend(groups)
        self.assertEqual(typed.periods, ["2026-01-05 至 2026-01-11"])
        self.assertEqual(len(typed.counts), 1)
        self.assertEqual(
            self.analyzer.trend_analysis(groups),
            typed.to_legacy()
        )

    def test_services_accept_trimmed_flow_and_text_values(self):
        dirty = self.df.copy()
        dirty["流程类型"] = " 工程公司录入承包商 "
        dirty["责任单位"] = [" 单位甲 ", "单位甲", " 单位乙", "单位乙 "]
        units = self.analyzer.unit_profile_units(dirty)
        self.assertIn("单位甲", units)
        self.assertIn("单位乙", units)

    def test_special_category_trend_keeps_zero_periods(self):
        first = self.df.copy()
        second = self.df.copy()
        second["时间周期"] = "2026-01-12 至 2026-01-18"
        second["周期开始日期"] = pd.Timestamp("2026-01-12")
        second["隐患分类"] = "施工/高处作业"
        result = self.analyzer.special_category_period_trend(
            [first, second], "用电"
        )
        self.assertEqual(
            result.periods,
            ["2026-01-05 至 2026-01-11", "2026-01-12 至 2026-01-18"]
        )
        self.assertEqual(result.counts, [1, 0])


if __name__ == "__main__":
    unittest.main()
