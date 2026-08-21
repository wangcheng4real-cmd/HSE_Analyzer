import tkinter as tk
from tkinter import messagebox
from dataclasses import asdict

from app.charts.chart import ChartFactory
from app.core.risk.rule_repository import RiskRules
from app.ui.components.chart_window import ChartWindow
from app.ui.theme import COLORS, FONTS, action_button


class RiskAnalysisController:
    """协调综合分析后台计算、规则配置和预警详情图。"""

    def refresh_analysis(self, force=False):
        bounds = self.app.analyzer.risk.date_bounds(
            self.app.hazard_state.df_all, self.app.brake_state.df_all
        )
        if bounds.empty:
            self.set_date_bounds(None)
            self.render_no_data()
            return
        self.set_date_bounds(bounds)
        start, end = self.selected_dates()
        if start is None:
            return
        period_type = self.period_type.get()
        rules = self.app.analyzer.risk.rule_repository.load()
        repository = self.app.analyzer.risk.rule_repository
        if repository.last_error and repository.last_error != self._last_rule_error:
            self._last_rule_error = repository.last_error
            self.app.write_log(repository.last_error)
            self.app.error_logger.error(repository.last_error)

        key = (
            self.app.hazard_state.revision,
            self.app.brake_state.revision,
            start, end, period_type, repository.revision,
            rules,
        )
        if not force and key in self._analysis_cache:
            dashboard, alerts = self._analysis_cache[key]
            self.render_results(dashboard, alerts)
            return

        self.render_loading()

        def worker(_report, _cancel):
            dashboard = self.app.analyzer.risk.dashboard(
                self.app.hazard_state.df_all, self.app.brake_state.df_all,
                start, end, period_type,
            )
            alerts = self.app.analyzer.risk.alerts(
                self.app.hazard_state.df_all, self.app.brake_state.df_all,
                start, end, period_type, rules,
            )
            return dashboard, alerts

        def success(result):
            self._analysis_cache[key] = result
            if len(self._analysis_cache) > 12:
                oldest = next(iter(self._analysis_cache))
                self._analysis_cache.pop(oldest, None)
            self.render_results(*result)
            self.app.write_log(
                f"综合分析已刷新：{start}至{end}，按{self.get_period_name()}统计"
            )

        def failed(exc, details, _cancelled=False):
            self.render_error(str(exc).splitlines()[0])
            self.app.report_error("综合分析", exc, details)

        self.app.submit_task(
            "综合分析", worker, success, failed, kind="analyzing"
        )

    def open_alert_chart(self, item):
        title_map = {
            "unit": "单位隐患趋势",
            "area": "区域隐患趋势",
            "special": "专项隐患趋势",
        }
        title = f"{item.name} - {title_map[item.kind]}"
        if item.kind == "unit":
            return ChartWindow.show_unit_risk_detail(
                self.app.root, item, title,
                xlabel=f"时间周期（按{self.get_period_name()}）",
                ylabel="隐患数量（条）",
            )
        figure = ChartFactory.risk_detail(
            list(item.periods), list(item.counts), list(item.history), title=title,
            xlabel=f"时间周期（按{self.get_period_name()}）", ylabel="隐患数量（条）",
        )
        ChartWindow.show(self.app.root, figure, title)

    def open_rule_settings(self):
        repository = self.app.analyzer.risk.rule_repository
        rules = repository.load()
        window = tk.Toplevel(self.app.root)
        window.withdraw()
        window.title("预警规则设置")
        window.resizable(True, True)
        window.transient(self.app.root)
        window.grab_set()

        header, tabs, canvas, shell = self._build_rule_dialog_layout(
            window, "综合预警规则",
            "所有规则只使用完整周期；百分比范围0～10000，周期和数量必须为正整数",
        )
        variables, frames, tab_buttons = {}, {}, {}
        titles = {"unit": "单位预警", "area": "区域预警", "special": "专项预警"}
        for kind, title in titles.items():
            frame = tk.Frame(shell, bg=COLORS["surface"])
            frames[kind] = frame
            variables[kind] = {}
            values = asdict(rules.for_kind(kind))
            for section_title, enabled_name, section_fields in self._rule_sections(kind):
                self._build_rule_setting_box(
                    frame, section_title, enabled_name, section_fields,
                    values, variables[kind],
                )

        def select(kind):
            for frame in frames.values():
                frame.pack_forget()
            frames[kind].pack(fill="both", expand=True)
            for value, button in tab_buttons.items():
                active = value == kind
                button.configure(
                    bg=COLORS["blue"] if active else COLORS["surface"],
                    fg="white" if active else COLORS["text"],
                )
            shell.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.yview_moveto(0)

        for kind, title in titles.items():
            button = tk.Button(
                tabs, text=title, command=lambda current=kind: select(current),
                relief="flat", borderwidth=0, cursor="hand2", padx=24, pady=8,
                font=("Microsoft YaHei", 10, "bold"),
            )
            button.pack(side="left", padx=(4, 0), pady=4)
            tab_buttons[kind] = button
        select("unit")

        buttons = tk.Frame(window, bg=COLORS["surface"], padx=24, pady=12)
        buttons.pack(fill="x")
        tk.Button(buttons, text="取消", command=window.destroy, relief="flat",
                  bg="#EDF3F9", fg=COLORS["text"], padx=18, pady=8,
                  font=FONTS["body"]).pack(side="left", padx=5)

        def save():
            try:
                values = {"schema_version": rules.schema_version}
                for kind, group in variables.items():
                    values[kind] = {
                        name: (variable.get() if isinstance(variable, tk.BooleanVar)
                               else variable.get().strip())
                        for name, variable in group.items()
                    }
                updated = RiskRules.from_mapping(values)
                repository.save(updated)
            except (ValueError, OSError) as exc:
                messagebox.showerror("保存失败", str(exc), parent=window)
                return
            window.destroy()
            self._analysis_cache.clear()
            self.refresh_analysis(force=True)
            self.app.write_log("预警规则设置已保存并生效")

        action_button(buttons, "保存", save, COLORS["blue"], "✓").pack(
            side="left", padx=5)
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.update_idletasks()
        width, height = 680, 720
        x = self.app.root.winfo_rootx() + max(0, (self.app.root.winfo_width() - width) // 2)
        y = self.app.root.winfo_rooty() + max(0, (self.app.root.winfo_height() - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.deiconify()
        window.lift()
        window.focus_force()

    def open_rule_help(self):
        rules = self.app.analyzer.risk.rule_repository.load()
        window = tk.Toplevel(self.app.root)
        window.title("综合预警规则说明")
        window.geometry("780x720")
        window.minsize(660, 560)
        window.transient(self.app.root)

        _header, tabs, canvas, body = self._build_rule_dialog_layout(
            window, "综合预警规则说明",
            f"当前规则版本：v{rules.schema_version}。预警只使用完整自然周期计算；总体大屏仍展示全部周期。",
        )
        frames, tab_buttons = {}, {}
        titles = {"unit": "单位预警", "area": "区域预警", "special": "专项预警"}
        common = tk.Frame(body, bg=COLORS["surface"])
        self._build_help_box(common, "黄橙红等级",
            "黄色：只命中1条普通规则。\n橙色：命中1条严重规则，或至少2条普通规则。\n"
            "红色：命中至少2条严重规则，或合计命中3条及以上规则。")
        self._build_help_box(common, "状态说明",
            "新增：当前触发、上一完整周期未触发。\n持续：当前和上一完整周期均触发。\n"
            "当前未命中规则的对象不进入预警列表。")
        common.pack(fill="x")
        for kind in titles:
            frame = tk.Frame(body, bg=COLORS["surface"])
            frames[kind] = frame
            for title, detail in self._rule_help_sections(kind, rules.for_kind(kind)):
                self._build_help_box(frame, title, detail)

        def select(kind):
            for frame in frames.values():
                frame.pack_forget()
            frames[kind].pack(fill="x", before=common)
            for value, button in tab_buttons.items():
                active = value == kind
                button.configure(bg=COLORS["blue"] if active else COLORS["surface"],
                                 fg="white" if active else COLORS["text"])
            body.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.yview_moveto(0)

        for kind, title in titles.items():
            button = tk.Button(tabs, text=title, command=lambda current=kind: select(current),
                               relief="flat", borderwidth=0, cursor="hand2",
                               padx=24, pady=8, font=("Microsoft YaHei", 10, "bold"))
            button.pack(side="left", padx=(4, 0), pady=4)
            tab_buttons[kind] = button
        select("unit")

        footer = tk.Frame(window, bg=COLORS["surface"], padx=24, pady=12)
        footer.pack(fill="x")
        tk.Button(footer, text="关闭", command=window.destroy, relief="flat",
                  bg=COLORS["blue"], fg="white", padx=24, pady=8,
                  font=FONTS["body"]).pack(anchor="e", pady=(14, 0))

    @staticmethod
    def _rule_sections(kind):
        sections = [
            ("历史基线异常", "baseline_enabled", [
                ("周历史窗口", "baseline_week_window", "期"),
                ("月历史窗口", "baseline_month_window", "期"),
                ("季度历史窗口", "baseline_quarter_window", "期"),
                ("增幅", "baseline_rate", "%"),
                ("绝对增量", "baseline_absolute", "条"),
            ]),
            ("连续恶化", "continuous_enabled", [
                ("连续周期数", "continuous_periods", "期"),
                ("首末增幅", "continuous_rate", "%"),
                ("首末绝对增量", "continuous_absolute", "条"),
            ]),
            ("A/B级异常", "ab_enabled", [
                ("A/B级数量", "ab_count", "条"),
                ("A/B级占比", "ab_ratio", "%"),
                ("占比最小总量", "ab_min_total", "条"),
            ]),
        ]
        if kind == "unit":
            sections.extend([
                ("重复发生", "repeat_enabled", [
                    ("二级隐患连续上升周期", "repeat_periods", "期"),
                ]),
                ("重复预警刹车", "brake_repeat_enabled", [
                    ("连续判断周期", "brake_repeat_periods", "期"),
                ]),
                ("隐患增多可能未及时预警", "missed_warning_enabled", [
                    ("环比增幅", "missed_warning_rate", "%"),
                    ("绝对增量", "missed_warning_absolute", "条"),
                ]),
            ])
        elif kind == "area":
            sections.extend([
                ("区域二级隐患连续恶化", "category_continuous_enabled", [
                    ("连续周期数", "category_continuous_periods", "期"),
                    ("首末增幅", "category_continuous_rate", "%"),
                    ("首末绝对增量", "category_continuous_absolute", "条"),
                ]),
                ("区域二级隐患突增", "category_surge_enabled", [
                    ("环比增幅", "category_surge_rate", "%"),
                    ("绝对增量", "category_surge_absolute", "条"),
                ]),
                ("区域风险跨单位扩散", "spread_enabled", [
                    ("本期最少责任单位", "spread_min_units", "家"),
                    ("较上期最少新增单位", "spread_unit_increase", "家"),
                    ("本期最少隐患数量", "spread_min_count", "条"),
                ]),
            ])
        return sections

    def _build_rule_dialog_layout(self, window, title, subtitle):
        header = tk.Frame(window, bg=COLORS["surface"], padx=24, pady=12)
        header.pack(fill="x")
        tk.Label(header, text=title, bg=COLORS["surface"], fg=COLORS["text"],
                 font=FONTS["section"]).pack(anchor="w")
        tk.Label(header, text=subtitle, bg=COLORS["surface"], fg=COLORS["muted"],
                 font=FONTS["card_subtitle"], justify="left", wraplength=700).pack(
                     anchor="w", pady=(4, 8))
        tabs = tk.Frame(header, bg=COLORS["surface"])
        tabs.pack(fill="x")
        outer = tk.Frame(window, bg=COLORS["surface"])
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=COLORS["surface"], highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=COLORS["surface"], padx=24, pady=8)
        content_id = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(content_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._bind_dialog_mousewheel(window, canvas)
        return header, tabs, canvas, body

    @staticmethod
    def _bind_dialog_mousewheel(window, canvas):
        def on_mousewheel(event):
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox or bbox[3] - bbox[1] <= canvas.winfo_height():
                canvas.yview_moveto(0)
                return "break"
            first, last = canvas.yview()
            if (event.delta > 0 and first <= 0) or (event.delta < 0 and last >= 1):
                return "break"
            canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"
        window.bind("<MouseWheel>", on_mousewheel)

    @staticmethod
    def _build_rule_setting_box(parent, title, enabled_name, section_fields,
                                values, variables):
        box = tk.Frame(parent, bg=COLORS["blue_soft"], highlightthickness=1,
                       highlightbackground=COLORS["border"])
        box.pack(fill="x", pady=6)
        enabled = tk.BooleanVar(value=values[enabled_name])
        variables[enabled_name] = enabled
        tk.Checkbutton(box, text=title, variable=enabled, bg=COLORS["blue_soft"],
                       activebackground=COLORS["blue_soft"], fg=COLORS["blue_dark"],
                       font=FONTS["card_title"], selectcolor=COLORS["surface"]).grid(
                           row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(9, 5))
        for row, (label, name, unit) in enumerate(section_fields, start=1):
            tk.Label(box, text=label, bg=COLORS["blue_soft"], fg=COLORS["text"],
                     font=FONTS["body"]).grid(row=row, column=0, sticky="w", padx=14, pady=4)
            value = values[name]
            variable = tk.StringVar(value=f"{value:g}" if isinstance(value, float) else str(value))
            variables[name] = variable
            tk.Entry(box, textvariable=variable, width=12, relief="solid", borderwidth=1,
                     font=FONTS["body"]).grid(row=row, column=1, padx=6, pady=4)
            tk.Label(box, text=unit, bg=COLORS["blue_soft"], fg=COLORS["muted"],
                     font=FONTS["body"]).grid(row=row, column=2, sticky="w", padx=(0, 12))
        box.grid_columnconfigure(0, weight=1)

    @staticmethod
    def _build_help_box(parent, title, detail):
        box = tk.Frame(parent, bg=COLORS["blue_soft"], highlightthickness=1,
                       highlightbackground=COLORS["border"], padx=14, pady=11)
        box.pack(fill="x", pady=5)
        tk.Label(box, text=title, bg=COLORS["blue_soft"], fg=COLORS["blue_dark"],
                 font=FONTS["card_title"]).pack(anchor="w")
        tk.Label(box, text=detail, bg=COLORS["blue_soft"], fg=COLORS["text"],
                 font=FONTS["body"], justify="left", wraplength=680).pack(
                     anchor="w", fill="x", pady=(5, 0))

    @staticmethod
    def _rule_help_sections(kind, rules):
        status = lambda enabled: "已启用" if enabled else "已停用"
        sections = [
            (f"历史基线异常（普通，{status(rules.baseline_enabled)}）",
             f"周前{rules.baseline_week_window}期、月前{rules.baseline_month_window}期、"
             f"季度前{rules.baseline_quarter_window}期；增幅达到{rules.baseline_rate:g}%且"
             f"增加不少于{rules.baseline_absolute}条。"),
            (f"连续恶化（普通，{status(rules.continuous_enabled)}）",
             f"最近{rules.continuous_periods}期严格上升，首末增幅达到{rules.continuous_rate:g}%且"
             f"增加不少于{rules.continuous_absolute}条。"),
            (f"A/B级异常（严重，{status(rules.ab_enabled)}）",
             f"A/B级达到{rules.ab_count}条，或总量达到{rules.ab_min_total}条且占比达到"
             f"{rules.ab_ratio:g}%。"),
        ]
        if kind == "unit":
            sections.extend([
                (f"重复发生（普通，{status(rules.repeat_enabled)}）",
                 f"同一单位同一二级分类最近{rules.repeat_periods}期严格逐期上升。"),
                (f"重复预警刹车（严重，{status(rules.brake_repeat_enabled)}）",
                 f"同问题类别连续{rules.brake_repeat_periods}期收到刹车，或单位刹车总量严格上升。"),
                (f"隐患增多可能未及时预警（严重，{status(rules.missed_warning_enabled)}）",
                 f"环比达到{rules.missed_warning_rate:g}%且增加不少于"
                f"{rules.missed_warning_absolute}条，本期无同类别预警刹车。"),
            ])
        elif kind == "area":
            sections.extend([
                (f"区域二级隐患连续恶化（普通，"
                 f"{status(rules.category_continuous_enabled)}）",
                 f"同一区域同一二级分类最近{rules.category_continuous_periods}期"
                 f"严格上升，首末增幅达到{rules.category_continuous_rate:g}%且增加"
                 f"不少于{rules.category_continuous_absolute}条。"),
                (f"区域二级隐患突增（普通，{status(rules.category_surge_enabled)}）",
                 f"同一区域同一二级分类环比达到{rules.category_surge_rate:g}%且"
                 f"增加不少于{rules.category_surge_absolute}条。"),
                (f"区域风险跨单位扩散（严重，{status(rules.spread_enabled)}）",
                 f"同一区域同一二级分类本期涉及不少于{rules.spread_min_units}家责任单位，"
                 f"较上期增加不少于{rules.spread_unit_increase}家，且隐患不少于"
                 f"{rules.spread_min_count}条。"),
            ])
        return sections
