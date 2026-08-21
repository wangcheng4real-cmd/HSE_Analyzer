import tkinter as tk
from tkinter import messagebox

from app.ui.controllers.chart_controller_mixin import ChartControllerMixin
from app.ui.components.ranked_selection_dialog import RankedSelectionDialog


class BrakeAnalysisController(ChartControllerMixin):
    """预警刹车分析弹窗、结果转换与图表交互。"""

    def _has_analysis_data(self):
        if self.state.df_all is None or self.state.df_all.empty:
            messagebox.showwarning("提示", "请先加载预警刹车数据")
            return False
        return True

    def _background_brake(self, name, operation, calculation, success, *args):
        if not self._has_analysis_data():
            return
        def worker(_report, _cancel):
            return self.app.run_cached(self.state, operation, args, calculation)
        def failed(exc, details, _cancelled=False):
            self.app.report_error(name, exc, details)
            messagebox.showerror("分析失败", str(exc).splitlines()[0])
        self.app.submit_task(name, worker, success, failed, kind="analyzing")

    def show_type_chart(self):
        if not self._has_analysis_data():
            return

        self._background_brake(
            "预警刹车类别分布", "type_counts",
            lambda: self.app.analyzer.brake.type_counts(self.state.df_all),
            self._show_type_chart_result
        )

    def _show_type_chart_result(self, counts):
        labels = list(counts.keys())
        values = list(counts.values())

        if sum(values) == 0:
            messagebox.showinfo("提示", "筛选后没有可统计的预警刹车数据")
            return

        self.show_pie(labels, values, title="预警刹车类别分布")
        self.app.write_log("已生成：预警刹车类别分布")

    def show_unit_top10(self):
        if not self._has_analysis_data():
            return

        self._background_brake(
            "预警刹车单位Top10", "unit_top10",
            lambda: self.app.analyzer.brake.unit_top10(self.state.df_all),
            self._show_unit_top10_result
        )

    def _show_unit_top10_result(self, counts):

        if not counts:
            messagebox.showinfo("提示", "筛选后没有可统计的责任单位数据")
            return

        self.show_bar(
            list(counts.keys()),
            list(counts.values()),
            title="预警刹车数量单位Top10",
            xlabel="责任单位",
            ylabel="预警刹车数量"
        )
        self.app.write_log("已生成：预警刹车数量单位Top10")

    def show_category_chart(self):
        if not self._has_analysis_data():
            return

        self._background_brake(
            "预警刹车问题类别Top10", "category_top10",
            lambda: self.app.analyzer.brake.category_top10(self.state.df_all),
            self._show_category_result
        )

    def _show_category_result(self, counts):

        if not counts:
            messagebox.showinfo("提示", "筛选后没有可统计的问题类别数据")
            return

        self.show_bar(
            list(counts.keys()),
            list(counts.values()),
            title="预警刹车问题类别Top10",
            xlabel="问题类别",
            ylabel="数量"
        )
        self.app.write_log("已生成：预警刹车问题类别Top10")

    def show_overall_weekly_trend(self):
        if not self._has_analysis_data():
            return

        period_type = self.period_type.get()
        self._background_brake(
            "预警刹车总体趋势", "overall_period_trend",
            lambda: self.app.analyzer.brake.overall_weekly_trend(
                self.state.df_all, period_type),
            self._show_overall_trend_result, period_type
        )

    def _show_overall_trend_result(self, result):
        periods = result["periods"]
        values = result["values"]

        if not periods:
            messagebox.showinfo(
                "提示",
                "筛选后没有可用的预警刹车发出时间数据"
            )
            return

        self.show_line(
            periods,
            values,
            title="预警刹车总体趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="预警刹车数量"
        )

        invalid_count = result["invalid_date_count"]
        log_text = f"已生成：预警刹车总体{self.get_period_name()}趋势"
        if invalid_count:
            log_text += f"（{invalid_count}条发出时间无效，未纳入趋势）"
        self.app.write_log(log_text)

    def _open_unit_selection(self, title, select_command):
        if not self._has_analysis_data():
            return
        self._background_brake(
            "预警刹车单位列表", "unit_counts",
            lambda: self.app.analyzer.brake.unit_counts(self.state.df_all),
            lambda counts: self._show_unit_selection_result(counts, select_command)
        )

    def _show_unit_selection_result(self, counts, select_command):
        if not counts:
            messagebox.showinfo("提示", "筛选后没有可用的责任单位数据")
            return
        RankedSelectionDialog(
            self.app.root, "选择单位", "单位", counts,
            select_command, count_label="预警刹车数量"
        )

    def open_unit_problem_category_top3_selection(self):
        self._open_unit_selection(
            "选择单位-预警刹车问题类别Top3",
            self.show_unit_problem_category_top3
        )

    def show_unit_problem_category_top3(self, unit):
        self._background_brake(
            f"{unit}问题类别Top3", "unit_problem_category_top3",
            lambda: self.app.analyzer.brake.unit_problem_category_top3(self.state.df_all, unit),
            lambda counts: self._show_unit_problem_result(unit, counts), unit
        )

    def _show_unit_problem_result(self, unit, counts):
        if not counts:
            messagebox.showinfo("提示", f"{unit}没有可统计的问题类别数据")
            return

        self.show_bar(
            list(counts.keys()),
            list(counts.values()),
            title=f"{unit}-预警刹车问题类别Top3",
            xlabel="问题类别",
            ylabel="数量"
        )
        self.app.write_log(f"已生成：{unit}预警刹车问题类别Top3")

    def open_unit_trend_selection(self):
        self._open_unit_selection(
            "选择单位-预警刹车趋势",
            self.show_unit_weekly_trend
        )

    def show_unit_weekly_trend(self, unit):
        period_type = self.period_type.get()
        self._background_brake(
            f"{unit}预警刹车趋势", "unit_period_trend",
            lambda: self.app.analyzer.brake.unit_weekly_trend(
                self.state.df_all, unit, period_type),
            lambda result: self._show_unit_trend_result(unit, result), unit, period_type
        )

    def _show_unit_trend_result(self, unit, result):
        periods = result["periods"]
        values = result["values"]

        if not periods:
            messagebox.showinfo("提示", f"{unit}没有可用的发出时间数据")
            return

        self.show_line(
            periods,
            values,
            title=f"{unit}-预警刹车趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="预警刹车数量"
        )

        log_text = f"已生成：{unit}预警刹车{self.get_period_name()}趋势"
        if result["invalid_date_count"]:
            log_text += f"（{result['invalid_date_count']}条发出时间无效）"
        self.app.write_log(log_text)

    def open_special_category_selection(self):
        self._background_brake(
            "预警刹车专项类别列表", "special_category_totals",
            lambda: self.app.analyzer.brake.special_category_totals(self.state.df_all),
            self._show_special_category_selection
        )

    def _show_special_category_selection(self, counts):
        if not counts:
            messagebox.showinfo("提示", "全部预警刹车数据中没有可用的问题类别")
            return
        RankedSelectionDialog(
            self.app.root, "选择问题类别", "分类", counts,
            self.open_special_unit_selection, count_label="预警刹车数量"
        )

    def open_special_unit_selection(self, category):
        period_type = self.period_type.get()
        self._background_brake(
            f"{category}专项单位列表", "special_category_unit_weekly_trend",
            lambda: self.app.analyzer.brake.special_category_unit_weekly_trend(
                self.state.df_all, category, period_type),
            lambda result: self._show_special_unit_selection(category, result),
            category, period_type
        )

    def _show_special_unit_selection(self, category, result):
        if not result["periods"]:
            messagebox.showinfo("提示", "没有可用于趋势分析的发出日期数据")
            return
        if not result["totals"]:
            messagebox.showinfo("提示", f"问题类别“{category}”没有可用的责任单位")
            return
        RankedSelectionDialog(
            self.app.root, "选择单位", "单位", result["totals"],
            lambda unit: self.show_special_unit_trend(category, unit, result),
            count_label="预警刹车数量"
        )

    def show_special_unit_trend(self, category, unit, result):
        values = result["series"].get(unit, [])
        self.show_line(
            result["periods"], values,
            title=f"{unit}-{category}预警刹车专项趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="预警刹车数量"
        )
        log_text = f"已生成：{unit}-{category}预警刹车专项趋势，累计{sum(values)}条"
        if result["invalid_date_count"]:
            log_text += f"（{result['invalid_date_count']}条发出日期无效）"
        self.app.write_log(log_text)

    def open_special_trend_category_selection(self):
        self._background_brake(
            "预警刹车专项趋势类别列表", "special_category_totals",
            lambda: self.app.analyzer.brake.special_category_totals(self.state.df_all),
            self._show_special_trend_category_selection
        )

    def _show_special_trend_category_selection(self, counts):
        if not counts:
            messagebox.showinfo("提示", "全部预警刹车数据中没有可用的问题类别")
            return
        RankedSelectionDialog(
            self.app.root, "选择问题类别", "分类", counts,
            self.show_special_category_trend, count_label="预警刹车数量"
        )

    def show_special_category_trend(self, category):
        period_type = self.period_type.get()
        self._background_brake(
            f"{category}专项趋势", "special_category_period_trend",
            lambda: self.app.analyzer.brake.special_category_period_trend(
                self.state.df_all, category, period_type),
            lambda result: self._show_special_category_trend_result(category, result),
            category, period_type
        )

    def _show_special_category_trend_result(self, category, result):
        if not result["periods"]:
            messagebox.showinfo("提示", "没有可用于趋势分析的发出日期数据")
            return
        self.show_line(
            result["periods"], result["values"],
            title=f"{category}-预警刹车专项趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="预警刹车数量"
        )
        log_text = (
            f"已生成：{category}预警刹车专项{self.get_period_name()}趋势，"
            f"累计{sum(result['values'])}条"
        )
        if result["invalid_date_count"]:
            log_text += f"（{result['invalid_date_count']}条发出日期无效）"
        self.app.write_log(log_text)


