import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.ui.controllers.risk_analysis_controller import RiskAnalysisController
from app.ui.components.chart_window import ChartWindow
from app.ui.pages.risk_page import RiskPage
from app.core.risk.results import RiskEvidence, RiskObject


class FakeFrame:
    def __init__(self):
        self.visible = False

    def pack_forget(self):
        self.visible = False

    def pack(self, **_kwargs):
        self.visible = True


class FakeButton:
    def __init__(self):
        self.options = {}

    def configure(self, **kwargs):
        self.options.update(kwargs)


class FakeCanvas:
    def __init__(self, bbox=(0, 0, 100, 1000), height=300, view=(0.0, 0.3)):
        self._bbox = bbox
        self._height = height
        self._view = view
        self.scrolls = []
        self.moveto = []

    def update_idletasks(self):
        pass

    def bbox(self, _name):
        return self._bbox

    def winfo_height(self):
        return self._height

    def yview(self):
        return self._view

    def yview_scroll(self, amount, unit):
        self.scrolls.append((amount, unit))

    def yview_moveto(self, value):
        self.moveto.append(value)


class FakeWindow:
    def bind(self, sequence, callback):
        self.sequence = sequence
        self.callback = callback


class RiskUiLogicTests(unittest.TestCase):
    def test_alert_category_switch_shows_only_selected_and_resets_scroll(self):
        page = object.__new__(RiskPage)
        page.alert_sections = {key: FakeFrame() for key in ("units", "areas", "specials")}
        page.alert_category_buttons = {
            key: FakeButton() for key in ("units", "areas", "specials")
        }
        page.canvas = FakeCanvas()
        page.select_alert_category("areas")
        self.assertEqual(page._active_alert_category, "areas")
        self.assertTrue(page.alert_sections["areas"].visible)
        self.assertFalse(page.alert_sections["units"].visible)
        self.assertEqual(page.canvas.moveto, [0])

    def test_dialog_mousewheel_always_stops_propagation(self):
        window = FakeWindow()
        canvas = FakeCanvas()
        RiskAnalysisController._bind_dialog_mousewheel(window, canvas)
        result = window.callback(SimpleNamespace(delta=-120))
        self.assertEqual(result, "break")
        self.assertEqual(canvas.scrolls, [(1, "units")])

        short_canvas = FakeCanvas(bbox=(0, 0, 100, 100), height=300)
        short_window = FakeWindow()
        RiskAnalysisController._bind_dialog_mousewheel(short_window, short_canvas)
        self.assertEqual(short_window.callback(SimpleNamespace(delta=-120)), "break")
        self.assertEqual(short_canvas.moveto, [0])

    def test_main_page_ignores_wheel_from_another_toplevel(self):
        page = object.__new__(RiskPage)
        root, dialog = object(), object()
        page.app = SimpleNamespace(root=root)
        page.canvas = FakeCanvas()
        event = SimpleNamespace(
            delta=-120,
            widget=SimpleNamespace(winfo_toplevel=lambda: dialog),
        )
        self.assertIsNone(page._on_mousewheel(event))
        self.assertFalse(page.canvas.scrolls)

    def test_rule_sections_are_independent_by_category(self):
        unit_titles = [item[0] for item in RiskAnalysisController._rule_sections("unit")]
        area_titles = [item[0] for item in RiskAnalysisController._rule_sections("area")]
        self.assertEqual(len(unit_titles), 6)
        self.assertEqual(len(area_titles), 6)
        self.assertNotIn("重复预警刹车", area_titles)
        self.assertIn("区域二级隐患连续恶化", area_titles)
        self.assertIn("区域二级隐患突增", area_titles)
        self.assertIn("区域风险跨单位扩散", area_titles)

    def test_unit_chart_uses_interactive_window_without_recalculation(self):
        controller = object.__new__(RiskAnalysisController)
        controller.app = SimpleNamespace(root=object())
        controller.get_period_name = lambda: "周"
        item = RiskObject(
            "unit", "甲单位", "黄色", "新增", "第2周", (),
            ("第1周", "第2周"), (1, 2), category_series=(("临时用电", (1, 2)),),
        )
        with patch(
            "app.ui.controllers.risk_analysis_controller.ChartWindow.show_unit_risk_detail"
        ) as show_unit:
            controller.open_alert_chart(item)
        show_unit.assert_called_once()

        area = RiskObject(
            "area", "一区", "黄色", "新增", "第2周", (),
            ("第1周", "第2周"), (1, 2),
        )
        with patch(
            "app.ui.controllers.risk_analysis_controller.ChartWindow.show"
        ) as show_regular:
            controller.open_alert_chart(area)
        show_regular.assert_called_once()

    def test_unit_category_summary_and_detail_options_share_one_order(self):
        item = RiskObject(
            "unit", "甲单位", "黄色", "新增", "第2周", (),
            ("第1周", "第2周"), (10, 20),
            category_series=(
                ("类别甲", (4, 6)), ("类别乙", (3, 5)), ("类别丙", (2, 4)),
                ("类别丁", (1, 3)), ("类别戊", (1, 2)), ("类别己", (0, 2)),
            ),
        )
        self.assertEqual(
            item.related_category_names,
            ("类别甲", "类别乙", "类别丙", "类别丁", "类别戊", "类别己"),
        )
        self.assertEqual(
            item.related_category_summary(),
            "涉及二级隐患：类别甲、类别乙、类别丙、类别丁、类别戊等6类",
        )
        category_map, display_map, displays = ChartWindow._unit_category_options(item)
        self.assertEqual(tuple(category_map), item.related_category_names)
        self.assertEqual(
            tuple(display_map[display] for display in displays),
            item.related_category_names,
        )
        self.assertEqual(displays[0], "类别甲（累计10条）")

    def test_unit_category_empty_state_is_shared(self):
        item = RiskObject(
            "unit", "甲单位", "黄色", "新增", "第2周", (),
            ("第1周", "第2周"), (1, 2),
        )
        self.assertEqual(
            item.related_category_summary(),
            "当前预警暂未归因到具体二级隐患类别",
        )
        self.assertEqual(ChartWindow._unit_category_options(item), ({}, {}, []))

        area = RiskObject(
            "area", "一区", "黄色", "新增", "第2周", (),
            ("第1周", "第2周"), (1, 2),
        )
        self.assertEqual(area.related_category_summary(), "")

    def test_card_and_unit_detail_share_evidence_text(self):
        evidence = RiskEvidence(
            "ab", "A/B级异常",
            "本期A/B级5条，占比25.0%（隐患总量20条）。"
            "A/B级类别明细：临时用电3条；高处作业2条",
            True, ("临时用电", "高处作业"),
            (("临时用电", 3), ("高处作业", 2)),
        )
        current = RiskObject(
            "unit", "甲单位", "橙色", "新增", "第2周", (evidence,),
            ("第1周", "第2周"), (10, 20),
            category_series=(("临时用电", (4, 7)), ("高处作业", (2, 3))),
        )
        self.assertEqual(
            current.evidence_summary,
            "• A/B级异常：" + evidence.detail,
        )
        explanation = ChartWindow._unit_explanation_text(current)
        self.assertIn(current.message, explanation)
        self.assertIn(current.related_category_summary(), explanation)
        self.assertIn("当前周期：第2周", explanation)
        self.assertIn(current.evidence_summary, explanation)

        improved = RiskObject(
            "unit", "甲单位", "橙色", "已改善", "第3周", (evidence,),
            ("第1周", "第2周", "第3周"), (10, 20, 8),
            last_trigger_period="第2周",
            category_series=(("临时用电", (4, 7, 2)),),
        )
        self.assertEqual(
            improved.evidence_summary,
            "最近触发证据：" + evidence.detail,
        )
        self.assertIn(improved.evidence_summary,
                      ChartWindow._unit_explanation_text(improved))


if __name__ == "__main__":
    unittest.main()
