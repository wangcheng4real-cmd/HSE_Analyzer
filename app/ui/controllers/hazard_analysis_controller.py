import tkinter as tk
from tkinter import messagebox, ttk

from app.ui.controllers.chart_controller_mixin import ChartControllerMixin
from app.ui.components.ranked_selection_dialog import RankedSelectionDialog


class HazardAnalysisController(ChartControllerMixin):
    """隐患分析弹窗、结果转换与图表交互。"""

    SPECIAL_COMMON_CATEGORIES = [
        "临时用电", "脚手架", "动火作业",
        "高处作业", "受限空间作业", "起重作业",
    ]

    def _background_hazard(self, name, operation, calculation, success, *args):
        state = self.app.hazard_state
        if state.df_all is None or state.df_all.empty:
            messagebox.showwarning("提示", "请先加载隐患数据")
            return
        def worker(_report, _cancel):
            return self.app.run_cached(state, operation, args, calculation)
        def failed(exc, details, _cancelled=False):
            self.app.report_error(name, exc, details)
            messagebox.showerror("分析失败", str(exc).splitlines()[0])
        self.app.submit_task(name, worker, success, failed, kind="analyzing")

    def level_chart(self):
        self._background_hazard(
            "隐患等级分析", "level_analysis",
            lambda: self.app.analyzer.hazard.level_analysis(self.app.hazard_state.df_all),
            self._show_level_result
        )

    def _show_level_result(self, data):
        self.show_pie(
            data.index.tolist(),
            data.values.tolist(),
            title="隐患等级分布"
        )


        self.write_log(
            "已生成：隐患等级分析"
        )



    def unit_chart(self):
        self._background_hazard(
            "单位Top10", "unit_analysis",
            lambda: self.app.analyzer.hazard.unit_analysis(self.app.hazard_state.df_all).head(10),
            self._show_unit_chart_result
        )

    def _show_unit_chart_result(self, data):
        self.show_bar(
            data.index.tolist(),
            data.values.tolist(),
            title="单位Top10"
        )


        self.write_log(
            "已生成：单位Top10"
        )



    def category_main_chart(self):
        self._background_hazard(
            "隐患分类分析", "category_main_analysis",
            lambda: self.app.analyzer.hazard.category_main_analysis(self.app.hazard_state.df_all),
            self._show_category_main_result
        )

    def _show_category_main_result(self, data):
        self.show_bar(
            data.index.tolist(),
            data.values.tolist(),
            title="隐患分类分析"
        )


        self.write_log(
            "已生成：隐患分类分析"
        )



    def category_sub_chart(self):
        self._background_hazard(
            "隐患细类Top10", "category_sub_analysis",
            lambda: self.app.analyzer.hazard.category_sub_analysis(self.app.hazard_state.df_all),
            self._show_category_sub_result
        )

    def _show_category_sub_result(self, data):
        self.show_bar(
            data.index.tolist(),
            data.values.tolist(),
            title="隐患细类TOP10"
        )


        self.write_log(
            "已生成：隐患细类TOP10"
        )



    def area_chart(self):
        self._background_hazard(
            "区域分析", "area_analysis",
            lambda: self.app.analyzer.hazard.area_analysis(self.app.hazard_state.df_all),
            self._show_area_chart_result
        )

    def _show_area_chart_result(self, data):
        self.show_bar(
            data.index.tolist(),
            data.values.tolist(),
            title="区域分析"
        )


        self.write_log(
            "已生成：区域分析"
        )



    def interface_chart(self):
        self._background_hazard(
            "接口队办分析", "interface_analysis",
            lambda: self.app.analyzer.hazard.interface_analysis(self.app.hazard_state.df_all),
            self._show_interface_result
        )

    def _show_interface_result(self, data):
        self.show_bar(
            data.index.tolist(),
            data.values.tolist(),
            title="接口队办分析"
        )


        self.write_log(
            "已生成：接口队办分析"
        )



    def ab_level_chart(self):
        self._background_hazard(
            "AB级隐患统计", "ab_level_analysis",
            lambda: self.app.analyzer.hazard.ab_level_analysis(self.app.hazard_state.df_all),
            self._show_ab_level_result
        )

    def _show_ab_level_result(self, data):
        self.show_bar(
            data.index.tolist(),
            data.values.tolist(),
            title="AB级隐患分类统计"
        )


        self.write_log(
            "已生成：AB级隐患分类统计"
        )
    # =========================
    # 单位隐患画像
    # =========================


    def unit_category_ui(self):
        self._background_hazard(
            "单位隐患类别列表", "unit_profile_units",
            lambda: self.app.analyzer.hazard.unit_profile_units(self.app.hazard_state.df_all),
            lambda counts: self._show_ranked_selection("选择单位", "单位", counts,
                                                        self.show_unit_category_top)
        )

    def _show_ranked_selection(self, title, item_kind, counts, callback):
        RankedSelectionDialog(
            self.app.root, title, item_kind, counts, callback
        )

    def show_unit_category_top(self, unit):
        self._background_hazard(
            f"{unit}隐患类别Top5", "unit_profile_top5",
            lambda: self.app.analyzer.hazard.unit_profile_top5(
                self.app.hazard_state.df_all, unit),
            lambda result: self._show_unit_category_result(unit, result), unit
        )

    def _show_unit_category_result(self, unit, result):
        self.show_bar(
            result.index.tolist(),
            result.values.tolist(),
            title=f"{unit}-隐患类别Top5"
        )


        self.write_log(
            f"已生成：{unit}隐患类别Top5"
        )



    def unit_ab_ui(self):
        self._background_hazard(
            "单位AB列表", "unit_ab_units",
            lambda: self.app.analyzer.hazard.unit_ab_units(self.app.hazard_state.df_all),
            lambda counts: self._show_ranked_selection("选择单位", "单位", counts,
                                                        self.show_unit_ab_top)
        )

    def show_unit_ab_top(self, unit):
        self._background_hazard(
            f"{unit}AB类隐患Top3", "unit_ab_top3",
            lambda: self.app.analyzer.hazard.unit_ab_top3(self.app.hazard_state.df_all, unit),
            lambda result: self._show_unit_ab_result(unit, result), unit
        )

    def _show_unit_ab_result(self, unit, result):
        if len(result)==0:

            self.write_log(
                f"{unit}无AB类隐患"
            )

            return


        self.show_bar(
            result.index.tolist(),
            result.values.tolist(),
            title=f"{unit}-AB类隐患TOP3"
        )


        self.write_log(
            f"已生成：{unit}AB类隐患TOP3"
        )



    def unit_team_ui(self):
        self._background_hazard(
            "单位班组列表", "unit_team_units",
            lambda: self.app.analyzer.hazard.unit_team_units(self.app.hazard_state.df_all),
            lambda counts: self._show_ranked_selection("选择单位", "单位", counts,
                                                        self.show_unit_team_top)
        )

    def show_unit_team_top(self, unit):
        self._background_hazard(
            f"{unit}责任班组Top5", "unit_team_top5",
            lambda: self.app.analyzer.hazard.unit_team_top5(self.app.hazard_state.df_all, unit),
            lambda result: self._show_unit_team_result(unit, result), unit
        )

    def _show_unit_team_result(self, unit, result):
        self.show_bar(
            result.index.tolist(),
            result.values.tolist(),
            title=f"{unit}-责任班组TOP5"
        )


        self.write_log(
            f"已生成：{unit}责任班组TOP5"
        )



    def unit_verify_chart(self):
        self._background_hazard(
            "单位按期验证率", "unit_verify_analysis",
            lambda: self.app.analyzer.hazard.unit_verify_analysis(self.app.hazard_state.df_all),
            self._show_unit_verify_result
        )

    def _show_unit_verify_result(self, result):
        units = [
            x[0]
            for x in result
        ]


        rates = [
            round(x[1]*100,2)
            for x in result
        ]


        self.show_bar(
            units,
            rates,
            title="各单位按期验证率"
        )


        self.write_log(
            "已生成：各单位按期验证率"
        )



    def unit_trend_ui(self):
        self._background_hazard(
            "单位趋势列表", "unit_trend_units",
            lambda: self.app.analyzer.hazard.unit_trend_units(self.app.hazard_state.df_all),
            lambda counts: self._show_ranked_selection("选择单位", "单位", counts,
                                                        self.show_unit_trend)
        )

    def show_unit_trend(self, unit):
        self._background_hazard(
            f"{unit}隐患趋势", "unit_period_trend",
            lambda: self.app.analyzer.hazard.unit_period_trend(
                self.app.hazard_state.df_list, unit),
            lambda result: self._show_unit_trend_result(unit, result), unit
        )

    def _show_unit_trend_result(self, unit, result):
        x = result.periods
        y = result.counts


        self.show_line(
            x,
            y,
            title=f"{unit}-隐患趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="数量"
        )


        self.write_log(
            f"已生成：{unit}隐患趋势"
        )
    # =========================
    # 专项隐患（区域）分析
    # =========================
    def special_trend_category_ui(self):
        if not self.app.hazard_state.df_list:
            messagebox.showwarning("提示", "请先添加并加载隐患数据")
            return
        self._background_hazard(
            "专项隐患趋势分类列表", "special_unit_category_totals",
            lambda: self.app.analyzer.hazard.special_unit_category_totals(
                self.app.hazard_state.df_list),
            self._show_special_trend_categories
        )

    def _show_special_trend_categories(self, category_totals):
        if not category_totals:
            messagebox.showinfo("提示", "当前数据中没有可用的专项隐患二级分类")
            return
        RankedSelectionDialog(
            self.app.root, "选择隐患二级分类", "分类", category_totals,
            self.show_special_category_trend,
            count_label="隐患数量",
            common_items=self.SPECIAL_COMMON_CATEGORIES,
        )
        self.write_log("已打开：专项隐患趋势分类选择窗口")

    def show_special_category_trend(self, category_name):
        self._background_hazard(
            f"{category_name}专项隐患趋势", "special_category_period_trend",
            lambda: self.app.analyzer.hazard.special_category_period_trend(
                self.app.hazard_state.df_list, category_name),
            lambda result: self._show_special_category_trend_result(
                category_name, result),
            category_name
        )

    def _show_special_category_trend_result(self, category_name, result):
        if result.empty:
            messagebox.showinfo("提示", "没有可用于趋势分析的时间周期数据")
            return
        self.show_line(
            result.periods, result.counts,
            title=f"{category_name}-专项隐患趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="隐患数量"
        )
        self.write_log(
            f"已生成：{category_name}专项隐患趋势，累计{sum(result.counts)}条"
        )

    def special_area_category_ui(self):

        if not self.app.hazard_state.df_list:
            messagebox.showwarning(
                "提示",
                "请先添加并加载隐患数据"
            )
            return

        self._background_hazard(
            "专项区域分类列表", "special_area_category_totals",
            lambda: self.app.analyzer.hazard.special_area_category_totals(
                self.app.hazard_state.df_list),
            self._show_special_area_categories
        )
        return

    def _show_special_area_categories(self, category_totals):

        if not category_totals:
            messagebox.showinfo(
                "提示",
                "当前数据中没有可用的专项隐患二级分类"
            )
            return

        RankedSelectionDialog(
            self.app.root,
            "选择隐患二级分类",
            "分类",
            category_totals,
            self.open_special_area_category,
            count_label="隐患数量",
            common_items=self.SPECIAL_COMMON_CATEGORIES,
        )
        self.write_log("已打开：专项隐患区域分析分类选择窗口")
        return

        win, frame = self.create_scroll_window(
            "专项隐患（区域）分析"
        )

        tk.Label(
            frame,
            text="选择隐患二级分类",
            font=("Microsoft YaHei", 11, "bold")
        ).pack(
            fill="x",
            padx=10,
            pady=(10, 5)
        )

        # =========================
        # 顶部下拉选择全部二级分类
        # =========================

        select_frame = tk.Frame(frame)

        select_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        # 按隐患数量从高到低排列
        sorted_category_items = sorted(
            category_totals.items(),
            key=lambda item: (
                -item[1],
                item[0]
            )
        )

        # 下拉框显示分类名称和数量
        category_display_values = [
            f"{category_name}（{count}条）"
            for category_name, count
            in sorted_category_items
        ]

        # 显示文字映射回真正的分类名称
        category_display_map = {
            f"{category_name}（{count}条）": category_name
            for category_name, count
            in sorted_category_items
        }

        category_var = tk.StringVar()

        category_combobox = ttk.Combobox(
            select_frame,
            textvariable=category_var,
            values=category_display_values,
            state="readonly"
        )

        category_combobox.pack(
            side="left",
            fill="x",
            expand=True
        )

        if category_display_values:
            category_combobox.current(0)

        def open_combobox_category():

            display_text = category_var.get()

            category_name = category_display_map.get(
                display_text
            )

            if not category_name:
                messagebox.showwarning(
                    "提示",
                    "请选择隐患二级分类"
                )
                return

            self.open_special_area_category(
                category_name
            )

        tk.Button(
            select_frame,
            text="确定",
            command=open_combobox_category
        ).pack(
            side="left",
            padx=(5, 0)
        )

        # =========================
        # 常用分类
        # =========================

        tk.Label(
            frame,
            text="常用分类",
            font=("Microsoft YaHei", 10, "bold")
        ).pack(
            fill="x",
            padx=10,
            pady=(15, 5)
        )

        default_categories = [
            "临时用电",
            "高处作业",
            "动火作业",
            "受限空间作业",
            "起重作业",
            "系统设备调试"
        ]

        # 常用分类也按数量从高到低排列
        sorted_default_categories = sorted(
            default_categories,
            key=lambda category_name: (
                -category_totals.get(category_name, 0),
                category_name
            )
        )

        for category_name in sorted_default_categories:

            count = category_totals.get(
                category_name,
                0
            )

            tk.Button(
                frame,
                text=f"{category_name}（{count}条）",
                command=lambda selected_category=category_name: (
                    self.open_special_area_category(
                        selected_category
                    )
                )
            ).pack(
                fill="x",
                padx=10,
                pady=3
            )

        self.write_log(
            "已打开：专项隐患区域分析分类选择窗口"
        )
    # =========================
    # 专项隐患（单位）分析
    # =========================
    def special_unit_category_ui(self):

        if not self.app.hazard_state.df_list:
            messagebox.showwarning(
                "提示",
                "请先添加并加载隐患数据"
            )
            return

        self._background_hazard(
            "专项单位分类列表", "special_unit_category_totals",
            lambda: self.app.analyzer.hazard.special_unit_category_totals(
                self.app.hazard_state.df_list),
            self._show_special_unit_categories
        )
        return

    def _show_special_unit_categories(self, category_totals):

        if not category_totals:
            messagebox.showinfo(
                "提示",
                "当前数据中没有可用的专项隐患二级分类"
            )
            return

        RankedSelectionDialog(
            self.app.root,
            "选择隐患二级分类",
            "分类",
            category_totals,
            self.open_special_unit_category,
            count_label="隐患数量",
            common_items=self.SPECIAL_COMMON_CATEGORIES,
        )
        self.write_log("已打开：专项隐患二级分类选择窗口")
        return

        win, frame = self.create_scroll_window(
            "专项隐患（单位）分析"
        )

        tk.Label(
            frame,
            text="选择隐患二级分类",
            font=("Microsoft YaHei", 11, "bold")
        ).pack(
            fill="x",
            padx=10,
            pady=(10, 5)
        )

        # 顶部支持手动选择全部二级分类
        select_frame = tk.Frame(frame)

        select_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        # 所有二级分类按数量从高到低排列
        sorted_category_items = sorted(
            category_totals.items(),
            key=lambda item: (
                -item[1],
                item[0]
            )
        )

        # 下拉框显示“分类名称（数量条）”
        category_display_values = [
            f"{category_name}（{count}条）"
            for category_name, count
            in sorted_category_items
        ]

        # 将显示文字映射回真正的分类名称
        category_display_map = {
            f"{category_name}（{count}条）": category_name
            for category_name, count
            in sorted_category_items
        }

        category_var = tk.StringVar()

        category_combobox = ttk.Combobox(
            select_frame,
            textvariable=category_var,
            values=category_display_values,
            state="readonly"
        )

        category_combobox.pack(
            side="left",
            fill="x",
            expand=True
        )

        # 默认选择数量最多的分类
        if category_display_values:
            category_combobox.current(0)


        def open_combobox_category():

            display_text = category_var.get()

            category_name = category_display_map.get(
                display_text
            )

            if not category_name:
                messagebox.showwarning(
                    "提示",
                    "请选择隐患二级分类"
                )
                return

            self.open_special_unit_category(
                category_name
            )


        tk.Button(
            select_frame,
            text="确定",
            command=open_combobox_category
        ).pack(
            side="left",
            padx=(5, 0)
        )

        tk.Label(
            frame,
            text="常用分类",
            font=("Microsoft YaHei", 10, "bold")
        ).pack(
            fill="x",
            padx=10,
            pady=(15, 5)
        )

        default_categories = [
            "临时用电",
            "高处作业",
            "动火作业",
            "受限空间作业",
            "起重作业",
            "系统设备调试"
        ]

        # 常用分类按照隐患数量从高到低排列
        sorted_default_categories = sorted(
            default_categories,
            key=lambda category_name: (
                -category_totals.get(category_name, 0),
                category_name
            )
        )

        for category_name in sorted_default_categories:

            count = category_totals.get(
                category_name,
                0
            )

            tk.Button(
                frame,
                text=f"{category_name}（{count}条）",
                command=lambda selected_category=category_name: (
                    self.open_special_unit_category(
                        selected_category
                    )
                )
            ).pack(
                fill="x",
                padx=10,
                pady=3
            )

        self.write_log(
            "已打开：专项隐患二级分类选择窗口"
        )
        #选择分类后显示区域
    def open_special_area_category(self, category_name):
        if not category_name:
            messagebox.showwarning("提示", "请选择隐患二级分类")
            return
        self._background_hazard(
            f"{category_name}专项区域趋势", "special_area_period_trend",
            lambda: self.app.analyzer.hazard.special_area_period_trend(
                self.app.hazard_state.df_list, category_name),
            lambda result: self._show_special_area_units(category_name, result),
            category_name
        )

    def _show_special_area_units(self, category_name, result):
        if not result.periods:
            messagebox.showinfo("提示", "没有可用于趋势分析的时间周期数据")
            return
        if not result.series:
            messagebox.showinfo("提示", "当前数据中没有符合条件的区域")
            return
        RankedSelectionDialog(
            self.app.root, "选择区域", "区域", result.totals,
            lambda area: self.show_special_area_trend(
                area, category_name, result.periods, result.series[area]
            )
        )

    def show_special_area_trend(
        self,
        area,
        category_name,
        periods,
        values
    ):

        self.show_line(
            [
                str(period)
                for period in periods
            ],
            values,
            title=f"{area}-{category_name}隐患趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="隐患数量"
        )

        total = sum(values)

        self.write_log(
            f"已生成：{area}-{category_name}隐患趋势，"
            f"累计{total}条"
        )
    def open_special_unit_category(self, category_name):
        if not category_name:
            messagebox.showwarning("提示", "请选择隐患二级分类")
            return
        self._background_hazard(
            f"{category_name}专项单位趋势", "special_unit_period_trend",
            lambda: self.app.analyzer.hazard.special_unit_period_trend(
                self.app.hazard_state.df_list, category_name),
            lambda result: self._show_special_unit_units(category_name, result),
            category_name
        )

    def _show_special_unit_units(self, category_name, result):
        if not result.periods:
            messagebox.showinfo("提示", "没有可用于趋势分析的时间周期数据")
            return
        if not result.series:
            messagebox.showinfo("提示", "当前数据中没有符合条件的责任单位")
            return
        RankedSelectionDialog(
            self.app.root, "选择单位", "单位", result.totals,
            lambda unit: self.show_special_unit_trend(
                unit, category_name, result.periods, result.series[unit]
            )
        )

    def show_special_unit_trend(
        self,
        unit,
        category_name,
        periods,
        values
    ):

        self.show_line(
            [
                str(period)
                for period in periods
            ],
            values,
            title=f"{unit}-{category_name}隐患趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="隐患数量"
        )

        total = sum(values)

        self.write_log(
            f"已生成：{unit}-{category_name}隐患趋势，"
            f"累计{total}条"
        )
    # =========================
    # 区域隐患画像
    # =========================


    def area_profile_ui(self):
        self._background_hazard(
            "区域隐患类别列表", "area_profile_areas",
            lambda: self.app.analyzer.hazard.area_profile_areas(self.app.hazard_state.df_all),
            lambda counts: self._show_ranked_selection("选择区域", "区域", counts,
                                                        self.show_area_category_top)
        )

    def show_area_category_top(self, area):
        self._background_hazard(
            f"{area}隐患类别Top5", "area_profile_top5",
            lambda: self.app.analyzer.hazard.area_profile_top5(self.app.hazard_state.df_all, area),
            lambda result: self._show_area_category_result(area, result), area
        )

    def _show_area_category_result(self, area, result):
        if len(result)==0:

            self.write_log(
                f"{area}无数据"
            )

            return



        self.show_bar(
            result.index.tolist(),
            result.values.tolist(),
            title=f"{area}-隐患类别Top5"
        )


        self.write_log(
            f"已生成：{area}隐患类别Top5"
        )



    def area_ab_ui(self):
        self._background_hazard(
            "区域AB列表", "area_ab_areas",
            lambda: self.app.analyzer.hazard.area_ab_areas(self.app.hazard_state.df_all),
            lambda counts: self._show_ranked_selection("选择区域", "区域", counts,
                                                        self.show_area_ab_top3)
        )

    def show_area_ab_top3(self, area):
        self._background_hazard(
            f"{area}AB类隐患Top3", "area_ab_top3",
            lambda: self.app.analyzer.hazard.area_ab_top3(self.app.hazard_state.df_all, area),
            lambda result: self._show_area_ab_result(area, result), area
        )

    def _show_area_ab_result(self, area, result):
        if len(result)==0:

            self.write_log(
                f"{area}无AB类隐患"
            )

            return



        self.show_bar(
            result.index.tolist(),
            result.values.tolist(),
            title=f"{area}-AB类隐患TOP3"
        )


        self.write_log(
            f"已生成：{area}AB类隐患TOP3"
        )



    def area_trend_ui(self):
        self._background_hazard(
            "区域趋势列表", "area_trend_areas",
            lambda: self.app.analyzer.hazard.area_trend_areas(self.app.hazard_state.df_all),
            lambda counts: self._show_ranked_selection("选择区域", "区域", counts,
                                                        self.show_area_trend)
        )

    def show_area_trend(self, area):
        self._background_hazard(
            f"{area}隐患趋势", "area_period_trend",
            lambda: self.app.analyzer.hazard.area_period_trend(self.app.hazard_state.df_list, area),
            lambda result: self._show_area_trend_result(area, result), area
        )

    def _show_area_trend_result(self, area, result):
        x = result.periods
        y = result.counts


        self.show_line(
            x,
            y,
            title=f"{area}-隐患数量趋势",
            xlabel=self.get_period_xlabel(),
            ylabel="数量"
        )


        self.write_log(
            f"已生成：{area}隐患趋势"
        )



    # =========================
    # 总体趋势
    # =========================


    def trend_chart(self):
        self._background_hazard(
            "总体趋势分析", "period_trend",
            lambda: self.app.analyzer.hazard.period_trend(self.app.hazard_state.df_list),
            self._show_trend_result
        )

    def _show_trend_result(self, result):
        x = result.periods
        y = result.counts


        self.show_line(
            x,
            y,
            title="总体趋势分析",
            xlabel=self.get_period_xlabel(),
            ylabel="数量"
        )


        self.write_log(
            "已生成：总体趋势分析"
        )



    # =========================
    # AB趋势
    # =========================


    def ab_trend_chart(self):
        self._background_hazard(
            "AB级隐患趋势", "ab_period_trend",
            lambda: self.app.analyzer.hazard.ab_period_trend(self.app.hazard_state.df_list),
            self._show_ab_trend_result
        )

    def _show_ab_trend_result(self, result):
        if result.empty:

            self.write_log(
                "无AB类隐患数据"
            )

            return



        x = result.periods
        y = result.counts



        self.show_line(
            x,
            y,
            title="AB级隐患趋势分析",
            xlabel=self.get_period_xlabel(),
            ylabel="数量"
        )


        self.write_log(
            "已生成：AB类隐患趋势"
        )
