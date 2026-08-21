import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.charts.chart import ChartFactory
from app.ui.controllers.risk_analysis_controller import RiskAnalysisController
from app.ui.theme import COLORS, FONTS, panel


class RiskPage(RiskAnalysisController):
    PERIOD_NAMES = {"week": "周", "month": "月", "quarter": "季度"}

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=COLORS["bg"])
        self.period_type = tk.StringVar(value="week")
        self.start_date = tk.StringVar()
        self.end_date = tk.StringVar()
        self._date_signature = None
        self._analysis_cache = {}
        self._last_rule_error = ""
        self._chart_canvases = {}
        self._figures = {}
        self._active_tab = "dashboard"
        self._active_alert_category = "units"
        self._mousewheel_binding = None
        self.period_buttons = {}

        self._build_toolbar()
        self._build_tabs()
        self._build_scroll_content()
        self._build_dashboard()
        self._build_alerts()
        self.show_tab("dashboard", refresh=False)

    def _build_toolbar(self):
        toolbar = panel(self.frame)
        toolbar.pack(fill="x", pady=(0, 10))
        row = tk.Frame(toolbar, bg=COLORS["surface"])
        row.pack(fill="x", padx=18, pady=13)

        tk.Label(row, text="分析时间段：", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Microsoft YaHei", 10, "bold")).pack(side="left")
        tk.Label(row, text="开始日期", bg=COLORS["surface"], fg=COLORS["muted"],
                 font=FONTS["body"]).pack(side="left", padx=(12, 5))
        self.start_box = ttk.Combobox(row, textvariable=self.start_date, width=12,
                                     state="disabled", font=FONTS["body"])
        self.start_box.pack(side="left")
        self.start_box.bind("<<ComboboxSelected>>", self._on_date_change)

        tk.Label(row, text="结束日期", bg=COLORS["surface"], fg=COLORS["muted"],
                 font=FONTS["body"]).pack(side="left", padx=(14, 5))
        self.end_box = ttk.Combobox(row, textvariable=self.end_date, width=12,
                                   state="disabled", font=FONTS["body"])
        self.end_box.pack(side="left")
        self.end_box.bind("<<ComboboxSelected>>", self._on_date_change)

        separator = tk.Frame(row, width=1, height=28, bg=COLORS["border"])
        separator.pack(side="left", padx=18)
        tk.Label(row, text="统计周期：", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Microsoft YaHei", 10, "bold")).pack(side="left")
        for value, text in (("week", "按周"), ("month", "按月"), ("quarter", "按季度")):
            button = tk.Button(
                row, text=text, command=lambda selected=value: self.select_period(selected),
                relief="flat", borderwidth=0, cursor="hand2",
                font=("Microsoft YaHei", 9, "bold"), padx=13, pady=7,
            )
            button.pack(side="left", padx=2)
            self.period_buttons[value] = button
        self._update_period_styles()

        self.rule_button = tk.Button(
            row, text="⚙  预警规则设置", command=self.open_rule_settings,
            relief="flat", borderwidth=1, cursor="hand2", bg=COLORS["blue_soft"],
            fg=COLORS["blue_dark"], activebackground="#DCEBFA",
            font=("Microsoft YaHei", 10, "bold"), padx=15, pady=8,
        )
        self.rule_button.pack(side="right")
        self.rule_help_button = tk.Button(
            row, text="?  规则说明", command=self.open_rule_help,
            relief="flat", borderwidth=1, cursor="hand2", bg="#EDF3F9",
            fg=COLORS["text"], activebackground="#E1EAF3",
            font=("Microsoft YaHei", 10, "bold"), padx=13, pady=8,
        )
        self.rule_help_button.pack(side="right", padx=(0, 8))

    def _build_tabs(self):
        shell = panel(self.frame)
        shell.pack(fill="x", pady=(0, 8))
        self.tab_buttons = {}
        for value, text, icon in (
            ("dashboard", "总体大屏", "▥"),
            ("alerts", "预警信息", "⚠"),
        ):
            button = tk.Button(
                shell, text=f"{icon}  {text}", command=lambda selected=value: self.show_tab(selected),
                relief="flat", borderwidth=0, cursor="hand2", padx=28, pady=11,
                font=("Microsoft YaHei", 11, "bold"),
            )
            button.pack(side="left", padx=(8, 0), pady=(4, 0))
            self.tab_buttons[value] = button

    def _build_scroll_content(self):
        shell = panel(self.frame)
        shell.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(shell, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=COLORS["bg"])
        self.content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(
            self.content_window, width=event.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.dashboard_frame = tk.Frame(self.content, bg=COLORS["bg"])
        self.alert_frame = tk.Frame(self.content, bg=COLORS["bg"])

    def _chart_card(self, parent, row, column):
        card = panel(parent)
        card.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
        body = tk.Frame(card, bg=COLORS["surface"], height=390)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        body.pack_propagate(False)
        return body

    def _build_dashboard(self):
        self.dashboard_frame.grid_columnconfigure(0, weight=1, uniform="charts")
        self.dashboard_frame.grid_columnconfigure(1, weight=1, uniform="charts")
        self.dashboard_frame.grid_rowconfigure(0, weight=1)
        self.dashboard_frame.grid_rowconfigure(1, weight=1)
        self.chart_hosts = {
            "hazard_levels": self._chart_card(self.dashboard_frame, 0, 0),
            "hazard_trend": self._chart_card(self.dashboard_frame, 0, 1),
            "brake_types": self._chart_card(self.dashboard_frame, 1, 0),
            "brake_trend": self._chart_card(self.dashboard_frame, 1, 1),
        }
        for key, host in self.chart_hosts.items():
            tk.Label(host, text="等待加载数据", bg=COLORS["surface"], fg=COLORS["muted"],
                     font=FONTS["body"]).place(relx=0.5, rely=0.5, anchor="center")

    def _build_alerts(self):
        self.alert_hosts = {}
        meta = panel(self.alert_frame, bg=COLORS["blue_soft"])
        meta.pack(fill="x", padx=5, pady=(5, 7))
        self.alert_meta = tk.Label(
            meta, text="等待生成预警信息", bg=COLORS["blue_soft"],
            fg=COLORS["blue_dark"], font=FONTS["body"], anchor="w",
            justify="left", wraplength=1200,
        )
        self.alert_meta.pack(fill="x", padx=16, pady=11)
        tabs = panel(self.alert_frame)
        tabs.pack(fill="x", padx=5, pady=(0, 7))
        self.alert_category_buttons = {}
        for key, title in (("units", "单位预警"), ("areas", "区域预警"),
                           ("specials", "专项预警")):
            button = tk.Button(
                tabs, text=title,
                command=lambda selected=key: self.select_alert_category(selected),
                relief="flat", borderwidth=0, cursor="hand2", padx=28, pady=10,
                font=("Microsoft YaHei", 10, "bold"),
            )
            button.pack(side="left", padx=(6, 0), pady=4)
            self.alert_category_buttons[key] = button

        self.alert_category_container = tk.Frame(self.alert_frame, bg=COLORS["bg"])
        self.alert_category_container.pack(fill="both", expand=True)
        self.alert_sections = {}
        descriptions = {
            "units": ("单位预警", "完整趋势、严重程度、重复发生及预警刹车联动", COLORS["blue"]),
            "areas": ("区域预警", "区域大类完整趋势、基线、连续恶化和A/B级", COLORS["purple"]),
            "specials": ("专项预警", "隐患第二级分类完整趋势、基线、连续恶化和A/B级", COLORS["orange"]),
        }
        for key, (title, description, color) in descriptions.items():
            section = panel(self.alert_category_container)
            self.alert_sections[key] = section
            head = tk.Frame(section, bg=COLORS["surface"])
            head.pack(fill="x", padx=18, pady=(14, 8))
            tk.Label(head, text=f"◆  {title}", bg=COLORS["surface"], fg=color,
                     font=FONTS["section"]).pack(side="left")
            tk.Label(head, text=description, bg=COLORS["surface"], fg=COLORS["muted"],
                     font=FONTS["card_subtitle"]).pack(side="left", padx=14)
            body = tk.Frame(section, bg=COLORS["surface"])
            body.pack(fill="x", padx=18, pady=(0, 14))
            self.alert_hosts[key] = body
            tk.Label(body, text="等待生成预警信息", bg=COLORS["surface"],
                     fg=COLORS["muted"], font=FONTS["body"]).pack(anchor="w", pady=8)
        self.select_alert_category("units", reset_scroll=False)

    def select_alert_category(self, key, reset_scroll=True):
        if key not in self.alert_sections:
            return
        self._active_alert_category = key
        for section in self.alert_sections.values():
            section.pack_forget()
        self.alert_sections[key].pack(fill="x", padx=5, pady=6)
        for value, button in self.alert_category_buttons.items():
            active = value == key
            button.configure(
                bg=COLORS["blue"] if active else COLORS["surface"],
                fg="white" if active else COLORS["text"],
                activebackground=COLORS["blue_dark"] if active else COLORS["blue_soft"],
                activeforeground="white" if active else COLORS["text"],
            )
        if reset_scroll:
            self.canvas.yview_moveto(0)

    def set_date_bounds(self, bounds):
        if bounds is None or bounds.empty:
            self._date_signature = None
            self.start_date.set("")
            self.end_date.set("")
            self.start_box.configure(values=(), state="disabled")
            self.end_box.configure(values=(), state="disabled")
            self._set_filter_enabled(False)
            return
        signature = (bounds.start, bounds.end)
        if signature == self._date_signature:
            return
        values = [item.strftime("%Y-%m-%d") for item in pd.date_range(bounds.start, bounds.end)]
        previous_start = self.start_date.get()
        previous_end = self.end_date.get()
        self.start_box.configure(values=values, state="readonly")
        self.end_box.configure(values=values, state="readonly")
        self.start_date.set(previous_start if previous_start in values else values[0])
        self.end_date.set(previous_end if previous_end in values else values[-1])
        self._date_signature = signature
        self._analysis_cache.clear()
        self._set_filter_enabled(True)

    def _set_filter_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for button in self.period_buttons.values():
            button.configure(state=state)
        self.rule_button.configure(state=state)
        self.rule_help_button.configure(state=state)

    def selected_dates(self):
        try:
            start = pd.Timestamp(self.start_date.get()).normalize()
            end = pd.Timestamp(self.end_date.get()).normalize()
        except (ValueError, TypeError):
            return None, None
        if start > end:
            self.render_error("开始日期不能晚于结束日期")
            return None, None
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def _on_date_change(self, _event=None):
        if self.start_date.get() > self.end_date.get():
            self.render_error("开始日期不能晚于结束日期")
            return
        self._analysis_cache.clear()
        self.refresh_analysis(force=True)

    def select_period(self, period_type):
        if period_type == self.period_type.get():
            return
        self.period_type.set(period_type)
        self._update_period_styles()
        self._analysis_cache.clear()
        self.refresh_analysis(force=True)

    def _update_period_styles(self):
        selected = self.period_type.get()
        for value, button in self.period_buttons.items():
            active = value == selected
            button.configure(
                bg=COLORS["blue"] if active else COLORS["blue_soft"],
                fg="white" if active else COLORS["blue_dark"],
                activebackground=COLORS["blue_dark"] if active else "#DCEBFA",
                activeforeground="white" if active else COLORS["blue_dark"],
            )

    def get_period_name(self):
        return self.PERIOD_NAMES[self.period_type.get()]

    def show_tab(self, name, refresh=True):
        self._active_tab = name
        self.dashboard_frame.pack_forget()
        self.alert_frame.pack_forget()
        target = self.dashboard_frame if name == "dashboard" else self.alert_frame
        target.pack(fill="both", expand=True, padx=3, pady=3)
        for value, button in self.tab_buttons.items():
            active = value == name
            button.configure(
                bg=COLORS["blue_soft"] if active else COLORS["surface"],
                fg=COLORS["blue_dark"] if active else COLORS["text"],
                activebackground=COLORS["blue_soft"],
            )
        self.canvas.yview_moveto(0)
        if refresh:
            self.refresh_analysis()

    def _replace_figure(self, key, figure):
        old_canvas = self._chart_canvases.pop(key, None)
        if old_canvas is not None:
            old_canvas.get_tk_widget().destroy()
        old_figure = self._figures.pop(key, None)
        if old_figure is not None:
            old_figure.clear()
        host = self.chart_hosts[key]
        for child in host.winfo_children():
            child.destroy()
        canvas = FigureCanvasTkAgg(figure, master=host)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvases[key] = canvas
        self._figures[key] = figure
        self._fit_embedded_chart(key)
        host.after(80, lambda current=key: self._fit_embedded_chart(current))

    def _fit_embedded_chart(self, key):
        """首次显示时主动按卡片客户区重绘，避免必须缩放窗口才完整。"""
        canvas = self._chart_canvases.get(key)
        host = self.chart_hosts.get(key)
        if canvas is None or host is None or not host.winfo_exists():
            return
        host.update_idletasks()
        width = host.winfo_width()
        height = host.winfo_height()
        if width < 200 or height < 200:
            host.after(80, lambda current=key: self._fit_embedded_chart(current))
            return
        canvas.resize(SimpleNamespace(width=width, height=height))
        canvas.draw()

    def _show_chart_message(self, key, title, message):
        figure = ChartFactory.donut([], [], title=title)
        ax = figure.axes[0]
        for text in list(ax.texts):
            text.remove()
        ax.text(0.5, 0.5, message, ha="center", va="center", color=COLORS["muted"],
                fontsize=11, wrap=True, transform=ax.transAxes)
        self._replace_figure(key, figure)

    def render_results(self, dashboard, alerts):
        period_name = self.get_period_name()
        if dashboard.hazard_message:
            self._show_chart_message("hazard_levels", "隐患分类（ABCD）",
                                     dashboard.hazard_message)
            self._show_chart_message("hazard_trend", f"总体隐患数量趋势（按{period_name}）",
                                     dashboard.hazard_message)
        else:
            self._replace_figure("hazard_levels", ChartFactory.donut(
                list(dashboard.hazard_levels), list(dashboard.hazard_levels.values()),
                "隐患分类（ABCD）", "隐患总数",
            ))
            self._replace_figure("hazard_trend", ChartFactory.line(
                dashboard.hazard_trend.periods, dashboard.hazard_trend.values,
                f"总体隐患数量趋势（按{period_name}）", "时间周期", "数量（条）",
            ))
        if dashboard.brake_message:
            self._show_chart_message("brake_types", "预警刹车类别（五类）",
                                     dashboard.brake_message)
            self._show_chart_message("brake_trend", f"预警刹车总体趋势（按{period_name}）",
                                     dashboard.brake_message)
        else:
            self._replace_figure("brake_types", ChartFactory.donut(
                list(dashboard.brake_types), list(dashboard.brake_types.values()),
                "预警刹车类别（五类）", "预警总数",
            ))
            self._replace_figure("brake_trend", ChartFactory.line(
                dashboard.brake_trend.periods, dashboard.brake_trend.values,
                f"预警刹车总体趋势（按{period_name}）", "时间周期", "数量（条）",
            ))
        self._render_alert_section("units", alerts.units)
        self._render_alert_section("areas", alerts.areas)
        self._render_alert_section("specials", alerts.specials)
        excluded = "、".join(alerts.excluded_periods) if alerts.excluded_periods else "无"
        meta_parts = [
            f"最近完整周期：{alerts.current_period or '无'}",
            f"排除的不完整周期：{excluded}",
            f"规则版本：{alerts.rule_version}",
        ]
        if alerts.unmatched_units:
            preview = "、".join(alerts.unmatched_units[:8])
            suffix = "等" if len(alerts.unmatched_units) > 8 else ""
            meta_parts.append(f"联动未匹配单位：{preview}{suffix}")
        if alerts.effect_pending:
            preview = "；".join(alerts.effect_pending[:4])
            suffix = "等" if len(alerts.effect_pending) > 4 else ""
            meta_parts.append(f"预警刹车联动提示：{preview}{suffix}")
        if alerts.message:
            meta_parts.append(alerts.message)
        self.alert_meta.configure(text="    |    ".join(meta_parts))

    def _render_alert_section(self, key, section):
        host = self.alert_hosts[key]
        for child in host.winfo_children():
            child.destroy()
        if section.message:
            tk.Label(host, text=section.message, bg=COLORS["surface"], fg=COLORS["muted"],
                     font=FONTS["body"]).pack(anchor="w", pady=10)
            return
        if not section.items:
            tk.Label(
                host, text="当前没有达到规则阈值的预警",
                bg=COLORS["surface"], fg=COLORS["muted"], font=FONTS["body"],
            ).pack(anchor="w", pady=10)
            return
        for item in section.items:
            self._build_risk_card(host, item)

    def _build_risk_card(self, host, item):
        styles = {
            "红色": ("#FFF1F2", "#F0B6BC", COLORS["red"]),
            "橙色": ("#FFF7EF", "#F2D2AF", COLORS["orange"]),
            "黄色": ("#FFFBEA", "#EADFA2", "#B58500"),
        }
        bg, border, color = styles.get(item.level, styles["黄色"])
        card = tk.Frame(host, bg=bg, highlightthickness=1,
                        highlightbackground=border, cursor="hand2")
        card.pack(fill="x", pady=5)
        badge = tk.Label(
            card, text=item.level,
            bg=color, fg="white", font=("Microsoft YaHei", 9, "bold"),
            padx=8, pady=4, cursor="hand2",
        )
        badge.pack(side="left", padx=12, pady=12, anchor="n")
        text = tk.Frame(card, bg=bg, cursor="hand2")
        text.pack(side="left", fill="both", expand=True, pady=9)
        title = tk.Label(text, text=item.message, bg=bg, fg=COLORS["text"],
                         font=FONTS["card_title"], anchor="w", cursor="hand2")
        title.pack(fill="x")
        clickable_widgets = [card, badge, text, title]
        if item.kind == "unit":
            categories = tk.Label(
                text, text=item.related_category_summary(), bg=bg,
                fg=COLORS["blue_dark"], font=FONTS["card_subtitle"],
                justify="left", anchor="w", wraplength=1000, cursor="hand2",
            )
            categories.pack(fill="x", pady=(5, 0))
            clickable_widgets.append(categories)
        details = tk.Label(
            text, text=item.evidence_summary, bg=bg, fg=COLORS["muted"],
            font=FONTS["card_subtitle"], justify="left", anchor="w",
            wraplength=1000, cursor="hand2",
        )
        details.pack(fill="x", pady=(5, 0))
        period = tk.Label(
            card, text=f"当前周期\n{item.current_period}", bg=bg,
            fg=COLORS["muted"], font=FONTS["card_subtitle"], justify="center",
        )
        period.pack(side="right", padx=12)
        clickable_widgets.append(details)
        for widget in clickable_widgets:
            widget.bind("<Button-1>", lambda _event, current=item: self.open_alert_chart(current))

    def render_loading(self):
        self.alert_meta.configure(text="正在按完整周期执行综合预警规则…")
        for key, title in (
            ("hazard_levels", "隐患分类（ABCD）"),
            ("hazard_trend", "总体隐患数量趋势"),
            ("brake_types", "预警刹车类别（五类）"),
            ("brake_trend", "预警刹车总体趋势"),
        ):
            self._show_chart_message(key, title, "正在生成综合分析数据…")

    def render_error(self, message):
        self.alert_meta.configure(text=f"综合预警计算失败：{message}")
        for key, title in (
            ("hazard_levels", "隐患分类（ABCD）"),
            ("hazard_trend", "总体隐患数量趋势"),
            ("brake_types", "预警刹车类别（五类）"),
            ("brake_trend", "预警刹车总体趋势"),
        ):
            self._show_chart_message(key, title, message)

    def render_no_data(self):
        self.render_error("请先在隐患分析或预警刹车分析中加载数据")
        self.alert_meta.configure(text="请先加载隐患数据；预警刹车数据用于单位联动评价")
        for host in self.alert_hosts.values():
            for child in host.winfo_children():
                child.destroy()
            tk.Label(host, text="请先在隐患分析中加载数据", bg=COLORS["surface"],
                     fg=COLORS["muted"], font=FONTS["body"]).pack(anchor="w", pady=10)

    def set_busy(self, busy, loading=False):
        state = "disabled" if busy else "normal"
        for button in self.period_buttons.values():
            button.configure(state=state)
        self.rule_button.configure(state=state)
        self.rule_help_button.configure(state=state)
        self.start_box.configure(state="disabled" if busy else (
            "readonly" if self._date_signature else "disabled"))
        self.end_box.configure(state="disabled" if busy else (
            "readonly" if self._date_signature else "disabled"))

    def _on_mousewheel(self, event):
        try:
            if event.widget.winfo_toplevel() is not self.app.root:
                return None
        except tk.TclError:
            return None
        bbox = self.canvas.bbox("all")
        if bbox and bbox[3] > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"
        return None

    def show(self):
        self.frame.pack(fill="both", expand=True)
        if self._mousewheel_binding is None:
            self._mousewheel_binding = self.app.root.bind(
                "<MouseWheel>", self._on_mousewheel, add="+"
            )
        self.app.refresh_status()
        self.refresh_analysis()

    def hide(self):
        if self._mousewheel_binding is not None:
            self.app.root.unbind("<MouseWheel>", self._mousewheel_binding)
            self._mousewheel_binding = None
        self.frame.pack_forget()
