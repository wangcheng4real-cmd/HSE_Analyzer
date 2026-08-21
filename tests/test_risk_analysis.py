import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.core.hazard.hazard_config import HazardConfig
from app.core.risk.risk_analyzer import RiskAnalyzer
from app.core.risk.rule_repository import (
    AreaRiskRules, DimensionRiskRules, RiskRuleRepository, RiskRules, UnitRiskRules,
)


WEEKS = ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26", "2026-02-02"]


def hazard_frame(rows):
    defaults = {
        "隐患单号": "H-1", "隐患级别": "C",
        "流程类型": "工程公司录入承包商", "状态": "完成",
        "责任单位": "甲单位", "区域": "厂区一/设施",
        "隐患分类": "施工/临时用电/配电箱",
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def hazard_counts(counts, unit="甲单位", level="C"):
    rows = []
    for period_index, count in enumerate(counts):
        for item in range(count):
            rows.append({
                "检查日期": WEEKS[period_index], "责任单位": unit,
                "隐患级别": level, "隐患单号": f"H-{period_index}-{item}",
            })
    return hazard_frame(rows)


def brake_frame(rows):
    defaults = {
        "预警编号": "B-1", "预警刹车类型": "整改通知",
        "责任单位": "甲单位", "状态": "完成",
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def disabled_rules(**overrides):
    values = dict(
        baseline_enabled=False, continuous_enabled=False, ab_enabled=False,
        repeat_enabled=False, brake_repeat_enabled=False,
        missed_warning_enabled=False,
    )
    values.update(overrides)
    disabled_dimension = DimensionRiskRules(
        baseline_enabled=False, continuous_enabled=False, ab_enabled=False,
    )
    return RiskRules(
        unit=UnitRiskRules(**values),
        area=disabled_dimension,
        special=disabled_dimension,
    )


def area_rules(**overrides):
    values = dict(
        baseline_enabled=False, continuous_enabled=False, ab_enabled=False,
        category_continuous_enabled=False, category_surge_enabled=False,
        spread_enabled=False,
    )
    values.update(overrides)
    return RiskRules(
        unit=UnitRiskRules(
            baseline_enabled=False, continuous_enabled=False, ab_enabled=False,
            repeat_enabled=False, brake_repeat_enabled=False,
            missed_warning_enabled=False,
        ),
        area=AreaRiskRules(**values),
        special=DimensionRiskRules(
            baseline_enabled=False, continuous_enabled=False, ab_enabled=False,
        ),
    )


class RiskAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = RiskAnalyzer(HazardConfig())

    def _alerts(self, hazard, rules, brake=None, start="2026-01-05", end="2026-02-08"):
        # Ensure the selectable union reaches the natural end of the last week.
        boundary = brake_frame([
            {"发出日期": start, "预警编号": "BOUNDARY-START", "责任单位": "边界单位"},
            {"发出日期": end, "预警编号": "BOUNDARY-END", "责任单位": "边界单位"},
        ])
        brake = pd.concat([brake, boundary], ignore_index=True) if brake is not None else boundary
        return self.analyzer.alerts(hazard, brake, start, end, "week", rules)

    def test_date_bounds_uses_union_of_both_sources(self):
        hazard = hazard_frame([{"检查日期": "2026-02-01"}])
        brake = brake_frame([{"发出日期": "2026-01-10"}, {"发出日期": "2026-03-20"}])
        bounds = self.analyzer.date_bounds(hazard, brake)
        self.assertEqual(bounds.start, pd.Timestamp("2026-01-10"))
        self.assertEqual(bounds.end, pd.Timestamp("2026-03-20"))

    def test_dashboard_keeps_partial_periods_and_fixed_categories(self):
        hazard = hazard_frame([
            {"检查日期": "2026-01-01", "隐患级别": "A级"},
            {"检查日期": "2026-01-10", "隐患级别": "B"},
        ])
        brake = brake_frame([
            {"发出日期": "2026-01-05", "预警编号": "1", "预警刹车类型": "通报批评"},
            {"发出日期": "2026-01-31", "预警编号": "2", "预警刹车类型": "管理约谈"},
        ])
        result = self.analyzer.dashboard(hazard, brake, "2026-01-01", "2026-01-31", "week")
        self.assertEqual(result.hazard_levels, {"A": 1, "B": 1, "C": 0, "D": 0})
        self.assertEqual(list(result.brake_types), [
            "通报批评", "整改通知", "挂牌督办", "管理约谈", "停工令"
        ])
        self.assertEqual(sum(result.brake_types.values()), 2)
        self.assertEqual(len(result.hazard_trend.periods), 5)

    def test_alerts_exclude_partial_boundary_periods(self):
        hazard = hazard_frame([
            {"检查日期": "2026-01-06"}, {"检查日期": "2026-01-12"},
            {"检查日期": "2026-01-24"},
        ])
        result = self.analyzer.alerts(
            hazard, None, "2026-01-06", "2026-01-24", "week", disabled_rules()
        )
        self.assertEqual(result.current_period, "2026-01-12至2026-01-18")
        self.assertEqual(len(result.excluded_periods), 2)

    def test_month_and_quarter_complete_period_boundaries(self):
        month_axis, month_labels, month_excluded = self.analyzer._complete_axis(
            pd.Timestamp("2026-01-15"), pd.Timestamp("2026-03-31"), "month"
        )
        self.assertEqual(month_labels, ["2026年02月", "2026年03月"])
        self.assertEqual(month_excluded, ["2026年01月"])
        quarter_axis, quarter_labels, quarter_excluded = self.analyzer._complete_axis(
            pd.Timestamp("2026-02-01"), pd.Timestamp("2026-09-30"), "quarter"
        )
        self.assertEqual(quarter_labels, ["2026年第2季度", "2026年第3季度"])
        self.assertEqual(quarter_excluded, ["2026年第1季度"])

    def test_baseline_rule_uses_history_rate_and_absolute_gate(self):
        result = self._alerts(
            hazard_counts([5, 5, 5, 12]),
            disabled_rules(baseline_enabled=True), end="2026-02-01",
        )
        item = result.units.items[0]
        self.assertEqual(item.status, "新增")
        self.assertEqual(item.level, "黄色")
        self.assertEqual(item.evidence[0].code, "baseline")
        self.assertIn("前3期均值5.0条", item.evidence[0].detail)
        self.assertEqual(item.evidence[0].related_categories, ("临时用电",))
        self.assertEqual(item.category_series[0][0], "临时用电")
        self.assertEqual(item.category_series[0][1], (5, 5, 5, 12))

    def test_baseline_attribution_excludes_non_contributing_category(self):
        rows = []
        for category, counts in (("贡献类别", [5, 5, 5, 12]), ("回落类别", [5, 5, 5, 4])):
            for period_index, count in enumerate(counts):
                for item in range(count):
                    rows.append({
                        "检查日期": WEEKS[period_index],
                        "隐患分类": f"施工/{category}/明细",
                        "隐患单号": f"{category}-{period_index}-{item}",
                    })
        result = self._alerts(
            hazard_frame(rows), disabled_rules(baseline_enabled=True), end="2026-02-01"
        )
        evidence = result.units.items[0].evidence[0]
        self.assertEqual(evidence.related_categories, ("贡献类别",))
        self.assertEqual([name for name, _values in result.units.items[0].category_series], ["贡献类别"])

    def test_zero_baseline_requires_absolute_minimum(self):
        result = self._alerts(
            hazard_counts([0, 0, 0, 5]),
            disabled_rules(baseline_enabled=True), end="2026-02-01",
        )
        self.assertEqual(result.units.items[0].evidence[0].code, "baseline")

    def test_continuous_rule_requires_strict_rise(self):
        rules = disabled_rules(continuous_enabled=True)
        triggered = self._alerts(hazard_counts([1, 3, 6]), rules, end="2026-01-25")
        interrupted = self._alerts(hazard_counts([1, 3, 3]), rules, end="2026-01-25")
        self.assertEqual(triggered.units.items[0].evidence[0].code, "continuous")
        self.assertEqual(
            triggered.units.items[0].evidence[0].related_categories,
            ("临时用电",),
        )
        self.assertFalse(interrupted.units.items)

    def test_dimensions_execute_independent_rule_configuration(self):
        off = DimensionRiskRules(
            baseline_enabled=False, continuous_enabled=False, ab_enabled=False,
        )
        area_only = DimensionRiskRules(
            baseline_enabled=True, baseline_rate=30, baseline_absolute=5,
            continuous_enabled=False, ab_enabled=False,
        )
        rules = RiskRules(
            unit=UnitRiskRules(
                baseline_enabled=False, continuous_enabled=False, ab_enabled=False,
                repeat_enabled=False, brake_repeat_enabled=False,
                missed_warning_enabled=False,
            ),
            area=area_only,
            special=off,
        )
        result = self._alerts(hazard_counts([5, 5, 5, 12]), rules, end="2026-02-01")
        self.assertFalse(result.units.items)
        self.assertEqual(result.areas.items[0].evidence[0].code, "baseline")
        self.assertFalse(result.specials.items)

    def test_area_category_continuous_requires_strict_rise_and_gates(self):
        triggered = self._alerts(
            hazard_counts([3, 5, 8]),
            area_rules(category_continuous_enabled=True), end="2026-01-25",
        )
        evidence = triggered.areas.items[0].evidence[0]
        self.assertEqual(evidence.code, "area_category_continuous")
        self.assertIn("3条→5条→8条", evidence.detail)
        self.assertEqual(evidence.related_categories, ("临时用电",))

        flat = self._alerts(
            hazard_counts([3, 5, 5]),
            area_rules(category_continuous_enabled=True), end="2026-01-25",
        )
        self.assertFalse(flat.areas.items)
        insufficient_absolute = self._alerts(
            hazard_counts([1, 2, 4]),
            area_rules(category_continuous_enabled=True), end="2026-01-25",
        )
        self.assertFalse(insufficient_absolute.areas.items)

    def test_area_category_surge_threshold_and_zero_base(self):
        triggered = self._alerts(
            hazard_counts([10, 15]), area_rules(category_surge_enabled=True),
            start="2026-01-05", end="2026-01-18",
        )
        evidence = triggered.areas.items[0].evidence[0]
        self.assertEqual(evidence.code, "area_category_surge")
        self.assertIn("上升50.0%", evidence.detail)
        self.assertIn("增加5条", evidence.detail)

        zero_base = self._alerts(
            hazard_counts([0, 5]), area_rules(category_surge_enabled=True),
            start="2026-01-05", end="2026-01-18",
        )
        self.assertIn("上期为0", zero_base.areas.items[0].evidence[0].detail)
        below_rate = self._alerts(
            hazard_counts([11, 16]), area_rules(category_surge_enabled=True),
            start="2026-01-05", end="2026-01-18",
        )
        self.assertFalse(below_rate.areas.items)

    def test_area_ab_evidence_lists_second_category_counts(self):
        rows = []
        for category, count, level in (
            ("临边防护、洞口防护", 3, "A级"), ("临时用电", 2, "B级"),
        ):
            rows.extend({
                "检查日期": WEEKS[0], "隐患单号": f"{category}-{index}",
                "隐患级别": level, "隐患分类": f"施工/{category}/明细",
            } for index in range(count))
        result = self._alerts(
            hazard_frame(rows), area_rules(ab_enabled=True),
            start="2026-01-05", end="2026-01-11",
        )
        evidence = result.areas.items[0].evidence[0]
        self.assertEqual(evidence.code, "ab")
        self.assertEqual(evidence.related_category_counts, (
            ("临边防护、洞口防护", 3), ("临时用电", 2),
        ))
        self.assertIn(
            "A/B级类别明细：临边防护、洞口防护3条；临时用电2条",
            evidence.detail,
        )

    def test_area_spread_uses_distinct_units_and_is_severe(self):
        rows = [{
            "检查日期": WEEKS[0], "责任单位": "甲单位", "隐患单号": "S0",
        }]
        for unit, count in (("甲单位", 2), ("乙单位", 2), ("丙单位", 1)):
            for index in range(count):
                rows.append({
                    "检查日期": WEEKS[1], "责任单位": unit,
                    "隐患单号": f"{unit}-{index}",
                })
        hazard = hazard_frame(rows)
        rules = area_rules(spread_enabled=True)
        without_brake = self._alerts(
            hazard, rules, start="2026-01-05", end="2026-01-18",
        )
        item = without_brake.areas.items[0]
        evidence = item.evidence[0]
        self.assertEqual(evidence.code, "area_spread")
        self.assertTrue(evidence.severe)
        self.assertEqual(item.level, "橙色")
        self.assertIn("本期涉及3家责任单位", evidence.detail)
        self.assertIn("上期1家、增加2家", evidence.detail)
        self.assertIn("共5条", evidence.detail)

        with_brake = self._alerts(
            hazard, rules,
            brake=brake_frame([{
                "发出日期": WEEKS[1], "预警编号": "AREA-B1",
                "责任单位": "甲单位", "问题类别": "临时用电",
            }]), start="2026-01-05", end="2026-01-18",
        )
        self.assertEqual(
            [e.code for e in with_brake.areas.items[0].evidence],
            [e.code for e in without_brake.areas.items[0].evidence],
        )

    def test_area_spread_skips_missing_unit_and_insufficient_growth(self):
        rows = []
        for period, units in ((WEEKS[0], ("甲", "乙")),
                              (WEEKS[1], ("甲", "乙", "丙"))):
            for unit in units:
                rows.extend({
                    "检查日期": period, "责任单位": unit,
                    "隐患单号": f"{period}-{unit}-{index}",
                } for index in range(2))
        result = self._alerts(
            hazard_frame(rows), area_rules(spread_enabled=True),
            start="2026-01-05", end="2026-01-18",
        )
        self.assertFalse(result.areas.items)

        missing_units = hazard_counts([1, 5])
        missing_units["责任单位"] = None
        missing = self._alerts(
            missing_units, area_rules(spread_enabled=True),
            start="2026-01-05", end="2026-01-18",
        )
        self.assertFalse(missing.areas.items)

    def test_ab_rule_normalizes_level_and_is_severe(self):
        result = self._alerts(
            hazard_counts([5], level="A级"), disabled_rules(ab_enabled=True),
            start="2026-01-05", end="2026-01-11",
        )
        item = result.units.items[0]
        self.assertEqual(item.level, "橙色")
        self.assertTrue(item.evidence[0].severe)
        self.assertEqual(item.evidence[0].related_categories, ("临时用电",))
        self.assertEqual(
            item.evidence[0].related_category_counts, (("临时用电", 5),)
        )
        self.assertIn("A/B级类别明细：临时用电5条", item.evidence[0].detail)

    def test_ab_category_counts_are_sorted_and_keep_punctuation(self):
        rows = []
        categories = (
            ("临边防护、洞口防护", 3, "A级"),
            ("A类别", 2, "B级"),
            ("B类别", 2, "A级"),
        )
        for category, count, level in categories:
            for index in range(count):
                rows.append({
                    "检查日期": WEEKS[0],
                    "隐患单号": f"{category}-{index}",
                    "隐患级别": level,
                    "隐患分类": f"施工/{category}/明细",
                })
        result = self._alerts(
            hazard_frame(rows), disabled_rules(ab_enabled=True),
            start="2026-01-05", end="2026-01-11",
        )
        evidence = result.units.items[0].evidence[0]
        self.assertEqual(evidence.related_category_counts, (
            ("临边防护、洞口防护", 3), ("A类别", 2), ("B类别", 2),
        ))
        self.assertIn(
            "A/B级类别明细：临边防护、洞口防护3条；A类别2条；B类别2条",
            evidence.detail,
        )

    def test_ab_rule_keeps_trigger_when_category_detail_is_missing(self):
        rows = [
            {
                "检查日期": WEEKS[0], "隐患单号": f"missing-{index}",
                "隐患级别": "A级", "隐患分类": "",
            }
            for index in range(5)
        ]
        result = self._alerts(
            hazard_frame(rows), disabled_rules(ab_enabled=True),
            start="2026-01-05", end="2026-01-11",
        )
        evidence = result.units.items[0].evidence[0]
        self.assertEqual(evidence.code, "ab")
        self.assertEqual(evidence.related_category_counts, ())
        self.assertIn("未取得A/B级二级隐患类别明细", evidence.detail)

    def test_repeat_rule_requires_unit_second_category_strict_rise(self):
        result = self._alerts(
            hazard_counts([1, 2, 3]), disabled_rules(repeat_enabled=True),
            end="2026-01-25",
        )
        evidence = result.units.items[0].evidence[0]
        self.assertEqual(evidence.code, "repeat")
        self.assertIn("临时用电", evidence.detail)
        self.assertIn("1条→2条→3条", evidence.detail)
        self.assertFalse(result.areas.items)
        self.assertFalse(result.specials.items)

        interrupted = self._alerts(
            hazard_counts([1, 2, 2]), disabled_rules(repeat_enabled=True),
            end="2026-01-25",
        )
        self.assertFalse(interrupted.units.items)

    def test_repeat_rule_merges_multiple_rising_categories(self):
        rows = []
        for category, counts in (("临时用电", [1, 2, 3]), ("作业行为", [2, 3, 4])):
            for period_index, count in enumerate(counts):
                for item in range(count):
                    rows.append({
                        "检查日期": WEEKS[period_index],
                        "隐患分类": f"施工/{category}/明细",
                        "隐患单号": f"{category}-{period_index}-{item}",
                    })
        result = self._alerts(
            hazard_frame(rows), disabled_rules(repeat_enabled=True),
            end="2026-01-25",
        )
        evidence = result.units.items[0].evidence[0]
        self.assertIn("临时用电", evidence.detail)
        self.assertIn("作业行为", evidence.detail)
        self.assertEqual(set(evidence.related_categories), {"临时用电", "作业行为"})
        self.assertEqual(result.units.items[0].category_series[0][0], "作业行为")

    def test_unit_category_detail_series_keeps_partial_period_and_zero(self):
        rows = []
        for period_index, count in zip((1, 2, 3), (1, 2, 3)):
            for item in range(count):
                rows.append({
                    "检查日期": WEEKS[period_index],
                    "隐患单号": f"partial-{period_index}-{item}",
                })
        result = self._alerts(
            hazard_frame(rows), disabled_rules(repeat_enabled=True),
            start="2026-01-06", end="2026-02-01",
        )
        item = result.units.items[0]
        self.assertEqual(len(item.periods), 4)
        self.assertEqual(item.category_series[0][1], (0, 1, 2, 3))

    def test_repeated_brake_rule_matches_category_or_total_rise(self):
        hazard = hazard_counts([1, 1, 1])
        brake = brake_frame([
            {"发出日期": WEEKS[0], "预警编号": "B1", "责任单位": "甲单位",
             "问题类别": "临时用电、作业行为"},
            {"发出日期": WEEKS[1], "预警编号": "B2", "责任单位": "甲单位",
             "问题类别": "临时用电"},
            {"发出日期": WEEKS[2], "预警编号": "B3", "责任单位": "甲单位",
             "问题类别": "临时用电", "预警刹车类型": "管理约谈"},
            {"发出日期": WEEKS[2], "预警编号": "B4", "责任单位": "未匹配单位",
             "问题类别": "动火作业"},
        ])
        result = self._alerts(
            hazard, disabled_rules(brake_repeat_enabled=True), brake=brake,
            end="2026-01-25",
        )
        item = result.units.items[0]
        self.assertEqual(item.evidence[0].code, "brake_repeat")
        self.assertEqual(item.level, "橙色")
        self.assertIn("临时用电", item.evidence[0].detail)
        self.assertIn("预警问题类别", item.evidence[0].detail)
        self.assertIn("1次→1次→1次", item.evidence[0].detail)
        self.assertEqual(item.evidence[0].related_categories, ("临时用电",))
        self.assertIn("未匹配单位", result.unmatched_units)

    def test_repeated_brake_total_strict_rise_triggers(self):
        hazard = hazard_counts([1, 1, 1])
        brake = brake_frame([
            {"发出日期": WEEKS[1], "预警编号": "T1", "问题类别": "临时用电"},
            {"发出日期": WEEKS[2], "预警编号": "T2", "问题类别": "动火作业"},
            {"发出日期": WEEKS[2], "预警编号": "T3", "问题类别": "作业行为"},
        ])
        result = self._alerts(
            hazard, disabled_rules(brake_repeat_enabled=True), brake=brake,
            end="2026-01-25",
        )
        evidence = result.units.items[0].evidence[0]
        self.assertIn("0次→1次→2次", evidence.detail)
        self.assertFalse(evidence.related_categories)
        self.assertFalse(result.units.items[0].category_series)

        flat = self._alerts(
            hazard, disabled_rules(brake_repeat_enabled=True),
            brake=brake_frame([
                {"发出日期": WEEKS[0], "预警编号": "F1", "问题类别": "类别一"},
                {"发出日期": WEEKS[1], "预警编号": "F2", "问题类别": "类别二"},
                {"发出日期": WEEKS[2], "预警编号": "F3", "问题类别": "类别三"},
            ]), end="2026-01-25",
        )
        self.assertFalse(flat.units.items)

    def test_unmatched_brake_problem_category_stays_in_evidence_only(self):
        hazard = hazard_counts([1, 1, 1])
        brake = brake_frame([
            {"发出日期": WEEKS[index], "预警编号": f"U{index}",
             "问题类别": "未登记类别"}
            for index in range(3)
        ])
        result = self._alerts(
            hazard, disabled_rules(brake_repeat_enabled=True), brake=brake,
            end="2026-01-25",
        )
        item = result.units.items[0]
        evidence = item.evidence[0]
        self.assertIn("“未登记类别”（预警问题类别）", evidence.detail)
        self.assertIn("未匹配到同名隐患二级分类，暂不展示趋势", evidence.detail)
        self.assertEqual(evidence.related_categories, ())
        self.assertEqual(item.category_series, ())

    def test_missed_warning_requires_rate_absolute_and_no_matching_brake(self):
        hazard = hazard_counts([10, 15])
        unrelated = brake_frame([{
            "发出日期": WEEKS[1], "预警编号": "M1", "责任单位": "乙单位",
            "问题类别": "临时用电",
        }])
        result = self._alerts(
            hazard, disabled_rules(missed_warning_enabled=True), brake=unrelated,
            start="2026-01-05", end="2026-01-18",
        )
        evidence = result.units.items[0].evidence[0]
        self.assertEqual(evidence.code, "missed_warning")
        self.assertIn("上升50.0%", evidence.detail)
        self.assertIn("增加5条", evidence.detail)
        self.assertEqual(evidence.related_categories, ("临时用电",))

        matching = brake_frame([{
            "发出日期": WEEKS[1], "预警编号": "M2", "责任单位": "甲单位",
            "问题类别": "临时用电",
        }])
        suppressed = self._alerts(
            hazard, disabled_rules(missed_warning_enabled=True), brake=matching,
            start="2026-01-05", end="2026-01-18",
        )
        self.assertFalse(suppressed.units.items)

        insufficient_rate = self._alerts(
            hazard_counts([11, 16]), disabled_rules(missed_warning_enabled=True),
            brake=unrelated, start="2026-01-05", end="2026-01-18",
        )
        self.assertFalse(insufficient_rate.units.items)
        insufficient_absolute = self._alerts(
            hazard_counts([2, 5]), disabled_rules(missed_warning_enabled=True),
            brake=unrelated, start="2026-01-05", end="2026-01-18",
        )
        self.assertFalse(insufficient_absolute.units.items)

        other_category = brake_frame([{
            "发出日期": WEEKS[1], "预警编号": "M3", "责任单位": "甲单位",
            "问题类别": "动火作业",
        }])
        still_triggered = self._alerts(
            hazard, disabled_rules(missed_warning_enabled=True), brake=other_category,
            start="2026-01-05", end="2026-01-18",
        )
        self.assertEqual(still_triggered.units.items[0].evidence[0].code, "missed_warning")

    def test_missed_warning_zero_base_and_missing_category_quality(self):
        zero_base = self._alerts(
            hazard_counts([0, 5]), disabled_rules(missed_warning_enabled=True),
            brake=brake_frame([{
                "发出日期": WEEKS[0], "预警编号": "Q1", "责任单位": "乙单位",
                "问题类别": "动火作业",
            }]), start="2026-01-05", end="2026-01-18",
        )
        self.assertEqual(zero_base.units.items[0].evidence[0].code, "missed_warning")
        self.assertIn("上期为0", zero_base.units.items[0].evidence[0].detail)

        no_category = self.analyzer.alerts(
            hazard_counts([10, 15]),
            brake_frame([
                {"发出日期": WEEKS[1], "预警编号": "Q2"},
                {"发出日期": "2026-01-18", "预警编号": "Q3", "责任单位": "边界单位"},
            ]),
            "2026-01-05", "2026-01-18", "week",
            disabled_rules(missed_warning_enabled=True),
        )
        self.assertFalse(no_category.units.items)
        self.assertTrue(any("问题类别" in message for message in no_category.effect_pending))

    def test_level_escalation_new_continuing_and_improved(self):
        rules = disabled_rules(
            ab_enabled=True, brake_repeat_enabled=True, brake_repeat_periods=2
        )
        hazard = hazard_counts([0, 5, 5], level="A")
        brake = brake_frame([
            {"发出日期": WEEKS[1], "预警编号": "L1", "责任单位": "甲单位",
             "问题类别": "临时用电"},
            {"发出日期": WEEKS[2], "预警编号": "L2", "责任单位": "甲单位",
             "问题类别": "临时用电"},
        ])
        current = self._alerts(hazard, rules, brake=brake, end="2026-01-25")
        self.assertEqual(current.units.items[0].status, "持续")
        self.assertEqual(current.units.items[0].level, "红色")

        improved_hazard = hazard_counts([0, 5, 0], level="A")
        improved = self._alerts(
            improved_hazard, disabled_rules(ab_enabled=True), end="2026-01-25"
        )
        self.assertFalse(improved.units.items)
        self.assertEqual(improved.units.improved[0].status, "已改善")
        self.assertEqual(improved.units.improved[0].category_series[0][0], "临时用电")

    def test_invalid_range_is_rejected(self):
        hazard = hazard_frame([{"检查日期": "2026-01-05"}])
        with self.assertRaisesRegex(ValueError, "开始日期"):
            self.analyzer.dashboard(hazard, None, "2026-01-06", "2026-01-05")


class RiskRuleRepositoryTests(unittest.TestCase):
    def test_frozen_app_initializes_and_persists_config_in_local_app_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            local_app_data = root / "local"
            bundled_config = bundle / "config" / "risk_rules.json"
            bundled_config.parent.mkdir(parents=True)
            bundled_config.write_text(json.dumps({
                "schema_version": 5,
                "unit": {}, "area": {"baseline_rate": 44}, "special": {},
            }), encoding="utf-8")
            with (
                patch("app.core.risk.rule_repository.sys.frozen", True, create=True),
                patch("app.core.risk.rule_repository.sys._MEIPASS", str(bundle), create=True),
                patch.dict("app.core.risk.rule_repository.os.environ", {
                    "LOCALAPPDATA": str(local_app_data),
                }),
            ):
                repository = RiskRuleRepository()
                expected_path = (
                    local_app_data / "HSE数据分析平台" / "config" / "risk_rules.json"
                )
                self.assertEqual(repository.path, expected_path)
                rules = repository.load()
                self.assertEqual(rules.area.baseline_rate, 44)
                self.assertTrue(expected_path.exists())

                updated = RiskRules(area=AreaRiskRules(baseline_rate=61))
                repository.save(updated)
                bundled_config.unlink()
                self.assertEqual(RiskRuleRepository().load().area.baseline_rate, 61)

    def test_defaults_save_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "risk_rules.json"
            repository = RiskRuleRepository(path)
            self.assertEqual(repository.load(), RiskRules())
            expected = RiskRules(
                unit=UnitRiskRules(baseline_rate=25),
                area=AreaRiskRules(baseline_rate=40),
                special=DimensionRiskRules(baseline_rate=75),
            )
            repository.save(expected)
            self.assertEqual(RiskRuleRepository(path).load(), expected)

    def test_old_three_rate_config_is_migrated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "risk_rules.json"
            path.write_text(json.dumps({
                "unit_rate": 20, "area_rate": 35, "special_rate": 45,
            }), encoding="utf-8")
            rules = RiskRuleRepository(path).load()
            self.assertEqual((rules.unit.baseline_rate, rules.area.baseline_rate,
                              rules.special.baseline_rate), (20, 35, 45))
            self.assertEqual(rules.unit.baseline_week_window, 3)
            self.assertEqual(rules.schema_version, 5)
            self.assertTrue(rules.unit.continuous_enabled)
            self.assertTrue(rules.unit.repeat_enabled)
            self.assertTrue(rules.unit.brake_repeat_enabled)
            self.assertTrue(rules.unit.missed_warning_enabled)

    def test_v2_config_preserves_limits_and_enables_all_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "risk_rules.json"
            path.write_text(json.dumps({
                "schema_version": 2,
                "unit_rate": 50, "area_rate": 45, "special_rate": 40,
                "continuous_enabled": False, "repeat_enabled": False,
                "brake_repeat_enabled": False, "effectiveness_enabled": False,
            }), encoding="utf-8")
            repository = RiskRuleRepository(path)
            rules = repository.load()
            self.assertEqual((rules.unit.baseline_rate, rules.area.baseline_rate,
                              rules.special.baseline_rate), (50, 45, 40))
            self.assertTrue(all((
                rules.unit.baseline_enabled, rules.unit.continuous_enabled,
                rules.unit.ab_enabled, rules.unit.repeat_enabled,
                rules.unit.brake_repeat_enabled, rules.unit.missed_warning_enabled,
            )))
            repository.save(rules)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema_version"], 5)
            self.assertNotIn("effectiveness_enabled", saved)
            self.assertEqual(set(saved), {"schema_version", "unit", "area", "special"})

    def test_v3_config_is_copied_into_independent_dimensions(self):
        migrated = RiskRules.from_mapping({
            "schema_version": 3,
            "baseline_week_window": 4,
            "unit_rate": 51, "area_rate": 42, "special_rate": 33,
            "continuous_enabled": False, "continuous_periods": 5,
            "ab_enabled": False, "ab_count": 8,
            "repeat_enabled": False, "missed_warning_rate": 65,
        })
        self.assertEqual(migrated.schema_version, 5)
        self.assertEqual(
            (migrated.unit.baseline_rate, migrated.area.baseline_rate,
             migrated.special.baseline_rate), (51, 42, 33),
        )
        for dimension in (migrated.unit, migrated.area, migrated.special):
            self.assertEqual(dimension.baseline_week_window, 4)
            self.assertFalse(dimension.continuous_enabled)
            self.assertEqual(dimension.continuous_periods, 5)
            self.assertFalse(dimension.ab_enabled)
            self.assertEqual(dimension.ab_count, 8)
        self.assertFalse(migrated.unit.repeat_enabled)
        self.assertEqual(migrated.unit.missed_warning_rate, 65)

    def test_v4_area_config_migrates_to_six_rules(self):
        migrated = RiskRules.from_mapping({
            "schema_version": 4,
            "unit": {},
            "area": {
                "baseline_rate": 47, "continuous_periods": 4,
                "ab_count": 7,
            },
            "special": {},
        })
        self.assertEqual(migrated.schema_version, 5)
        self.assertEqual(migrated.area.baseline_rate, 47)
        self.assertEqual(migrated.area.continuous_periods, 4)
        self.assertEqual(migrated.area.ab_count, 7)
        self.assertTrue(migrated.area.category_continuous_enabled)
        self.assertEqual(migrated.area.category_continuous_periods, 3)
        self.assertTrue(migrated.area.category_surge_enabled)
        self.assertEqual(migrated.area.category_surge_rate, 50)
        self.assertTrue(migrated.area.spread_enabled)
        self.assertEqual(migrated.area.spread_min_units, 3)

    def test_invalid_file_falls_back_and_validation_rejects_bad_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "risk_rules.json"
            path.write_text("not-json", encoding="utf-8")
            repository = RiskRuleRepository(path)
            self.assertEqual(repository.load(), RiskRules())
            self.assertTrue(repository.last_error)
        with self.assertRaises(ValueError):
            RiskRules.from_mapping({"unit_rate": -1})
        with self.assertRaises(ValueError):
            RiskRules.from_mapping({"repeat_periods": 0})
        with self.assertRaises(ValueError):
            RiskRules.from_mapping({
                "schema_version": 5, "unit": {}, "special": {},
                "area": {"spread_min_units": 0},
            })


if __name__ == "__main__":
    unittest.main()
