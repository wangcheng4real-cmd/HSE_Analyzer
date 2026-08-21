import io
import unittest

from matplotlib.figure import Figure

from app.charts.chart import ChartFactory


class ChartFactoryTests(unittest.TestCase):
    def assert_exportable(self, figure):
        self.assertIsInstance(figure, Figure)
        output = io.BytesIO()
        figure.savefig(output, format="png")
        self.assertGreater(len(output.getvalue()), 100)

    def test_bar_returns_exportable_figure(self):
        self.assert_exportable(ChartFactory.bar(["A", "B"], [1, 2], "柱状图"))

    def test_pie_returns_exportable_figure(self):
        figure = ChartFactory.pie(["A", "B"], [1, 2], "饼图")
        self.assertEqual(len(figure.axes), 2)
        self.assert_exportable(figure)

    def test_line_returns_exportable_figure(self):
        self.assert_exportable(ChartFactory.line(["第一周", "第二周"], [0, 3], "趋势"))

    def test_donut_and_multi_line_return_exportable_figures(self):
        self.assert_exportable(ChartFactory.donut(["A", "B"], [2, 3], "构成"))
        self.assert_exportable(ChartFactory.multi_line(
            ["第1周", "第2周"], {"甲单位": [1, 2], "乙单位": [0, 1]}, "趋势"
        ))

    def test_period_labels_are_compact_and_long_axes_are_sampled(self):
        labels = [
            f"2026-06-{day:02d}至2026-06-{day + 6:02d}"
            for day in range(1, 13)
        ]
        figure = ChartFactory.line(labels, list(range(12)), "周趋势")
        axis_labels = [item.get_text() for item in figure.axes[0].get_xticklabels()]
        self.assertLessEqual(len(axis_labels), 9)
        self.assertEqual(axis_labels[0], "06/01–06/07")
        self.assertEqual(axis_labels[-1], "06/12–06/18")
        self.assertEqual(
            ChartFactory.compact_period_label(
                "2026-06-01 至 2026-06-07"
            ),
            "06/01–06/07",
        )
        self.assertEqual(
            ChartFactory.compact_period_label("2026年06月"), "2026-06"
        )
        self.assertEqual(
            ChartFactory.compact_period_label("2026年第2季度"), "2026 Q2"
        )

    def test_risk_detail_returns_exportable_figure(self):
        from app.core.risk.results import PeriodRisk, RiskEvidence
        history = [PeriodRisk(
            "2026-06-01至2026-06-07", "黄色",
            (RiskEvidence("baseline", "历史基线异常", "示例证据"),),
        )]
        self.assert_exportable(ChartFactory.risk_detail(
            ["2026-06-01至2026-06-07"], [10], history, "风险详情"
        ))

    def test_unit_risk_detail_and_category_update(self):
        periods = ["2026-06-01至2026-06-07", "2026-06-08至2026-06-14"]
        figure = ChartFactory.unit_risk_detail(
            periods, [5, 8], "临时用电", [2, 4], title="单位详情"
        )
        self.assertEqual(len(figure.axes), 2)
        self.assertFalse(any(axis.tables for axis in figure.axes))
        self.assertIn("临时用电", figure.axes[1].get_title())
        ChartFactory.update_unit_risk_category(
            figure, periods, [1, 3], "作业行为", "时间周期", "数量（条）"
        )
        self.assertIn("作业行为", figure.axes[1].get_title())
        self.assertEqual(list(figure.axes[1].lines[0].get_ydata()), [1, 3])
        self.assert_exportable(figure)

    def test_unit_risk_detail_empty_category_state(self):
        figure = ChartFactory.unit_risk_detail(["第1周"], [3], title="单位详情")
        self.assertFalse(figure.axes[1].axison)
        self.assertIn("暂未归因", figure.axes[1].texts[0].get_text())
        self.assert_exportable(figure)

    def test_figures_are_independent(self):
        first = ChartFactory.bar(["A"], [1])
        second = ChartFactory.bar(["B"], [2])
        self.assertIsNot(first, second)
        self.assertEqual(first.axes[0].get_xticklabels()[0].get_text(), "A")
        self.assertEqual(second.axes[0].get_xticklabels()[0].get_text(), "B")


if __name__ == "__main__":
    unittest.main()
