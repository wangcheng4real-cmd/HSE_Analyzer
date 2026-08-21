import unittest

import pandas as pd

from app.core.brake.brake_analyzer import BrakeAnalyzer


class BrakeSpecialTrendTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = BrakeAnalyzer()
        self.df = pd.DataFrame({
            "预警编号": ["1", "2", "3", "4"],
            "预警刹车类型": ["通报批评", "整改通知", "管理约谈", "停工令"],
            "责任单位": ["单位甲", "单位甲", "单位乙", "单位甲"],
            "问题类别": ["高处作业，临时用电", "高处作业", "动火作业", "高处作业"],
            "发出日期": ["2026-01-05", "2026-01-19", "2026-01-06", "无效日期"],
        })

    def test_categories_use_all_brake_types_and_split_multiple_values(self):
        totals = self.analyzer.special_category_totals(self.df)
        self.assertEqual(totals["高处作业"], 3)
        self.assertEqual(totals["临时用电"], 1)
        self.assertEqual(totals["动火作业"], 1)

    def test_unit_trend_uses_natural_weeks_and_fills_zero(self):
        result = self.analyzer.special_category_unit_weekly_trend(
            self.df, "高处作业"
        )
        self.assertEqual(result["totals"], {"单位甲": 3})
        self.assertEqual(
            result["periods"],
            [
                "2026-01-05至2026-01-11",
                "2026-01-12至2026-01-18",
                "2026-01-19至2026-01-25",
            ]
        )
        self.assertEqual(result["series"]["单位甲"], [1, 0, 1])
        self.assertEqual(result["invalid_date_count"], 1)

    def test_month_and_quarter_periods(self):
        monthly = self.analyzer.special_category_unit_weekly_trend(
            self.df, "高处作业", "month"
        )
        quarterly = self.analyzer.special_category_unit_weekly_trend(
            self.df, "高处作业", "quarter"
        )
        self.assertEqual(monthly["periods"], ["2026年01月"])
        self.assertEqual(monthly["series"]["单位甲"], [2])
        self.assertEqual(quarterly["periods"], ["2026年第1季度"])
        self.assertEqual(quarterly["series"]["单位甲"], [2])

    def test_category_trend_counts_records_without_units(self):
        source = pd.DataFrame({
            "预警编号": ["a", "b", "c"],
            "预警刹车类型": ["通报批评", "整改通知", "管理约谈"],
            "责任单位": [None, "单位甲", "单位乙"],
            "问题类别": ["临时用电", "临时用电", "动火作业"],
            "发出日期": ["2026-01-05", "2026-02-06", "2026-04-01"],
        })
        result = self.analyzer.special_category_period_trend(
            source, "临时用电", "month"
        )
        self.assertEqual(
            result["periods"],
            ["2026年01月", "2026年02月", "2026年03月", "2026年04月"]
        )
        self.assertEqual(result["values"], [1, 1, 0, 0])


if __name__ == "__main__":
    unittest.main()
