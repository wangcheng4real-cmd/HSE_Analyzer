import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.ui.theme import COLORS, panel, action_button, set_feature_card_enabled
from app.ui.controllers.brake_analysis_controller import BrakeAnalysisController
from app.ui.components.scrollable_dialog import create_scrollable_dialog
from app.ui.components.dashboard_panel import build_dashboard_sections
from app.ui.components.file_table import create_file_table


class BrakePage(BrakeAnalysisController):
    BRAKE_TYPES = ["通报批评", "整改通知", "挂牌督办", "管理约谈", "停工令"]

    # 新版预警刹车仪表盘布局。
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.state = self.app.brake_state
        self.period_type = tk.StringVar(value=self.state.period_type)
        self.period_buttons = {}
        self.frame = tk.Frame(parent, bg=COLORS["bg"])
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self._build_dashboard_files()
        self._build_dashboard_features()

    def _build_dashboard_files(self):
        left = panel(self.frame, width=330)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_propagate(False)
        tk.Label(left, text="▰  预警刹车文件管理", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=18, pady=(16, 12))
        self.file_action_buttons = []
        button = action_button(left, "添加预警刹车文件", self.add_files, COLORS["blue"], "＋")
        button.pack(
            fill="x", padx=18, pady=4)
        self.file_action_buttons.append(button)
        ops = tk.Frame(left, bg=COLORS["surface"])
        ops.pack(fill="x", padx=14, pady=4)
        button = action_button(ops, "删除选中", self.remove_selected_file, "#E88728", "－")
        button.pack(
            side="left", fill="x", expand=True, padx=4)
        self.file_action_buttons.append(button)
        button = action_button(ops, "清空全部", self.clear_all_files, COLORS["red"], "×")
        button.pack(
            side="left", fill="x", expand=True, padx=4)
        self.file_action_buttons.append(button)
        button = action_button(left, "加载全部数据", self.load_data, "#31A35B", "⇧")
        button.pack(
            fill="x", padx=18, pady=(4, 12))
        self.file_action_buttons.append(button)
        self.cancel_button = action_button(left, "取消加载", self.app.cancel_loading,
                                           COLORS["muted"], "■")
        self.cancel_button.pack(fill="x", padx=18, pady=(0, 8))
        self.cancel_button.configure(state="disabled")
        tk.Label(left, text="统计周期", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", padx=18, pady=(2, 5))
        period_row = tk.Frame(left, bg=COLORS["surface"])
        period_row.pack(fill="x", padx=18, pady=(0, 10))
        for value, text in (("week", "按周"), ("month", "按月"), ("quarter", "按季度")):
            button = tk.Button(
                period_row, text=text,
                command=lambda selected=value: self.select_period(selected),
                relief="flat", borderwidth=0, cursor="hand2",
                font=("Microsoft YaHei", 9, "bold"), padx=8, pady=7
            )
            button.pack(side="left", fill="x", expand=True, padx=2)
            self.period_buttons[value] = button
        self.update_period_button_styles()
        self.progress_var = tk.DoubleVar()
        self.progress_text = tk.StringVar(value="等待加载数据")
        ttk.Progressbar(left, variable=self.progress_var, maximum=100,
                        style="HSE.Horizontal.TProgressbar").pack(fill="x", padx=18)
        tk.Label(left, textvariable=self.progress_text, bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("Microsoft YaHei", 8), wraplength=285).pack(fill="x", padx=18, pady=(4, 10))
        self.type_summary_var = tk.StringVar(value="已识别：暂无文件")
        tk.Label(left, textvariable=self.type_summary_var, bg=COLORS["surface"], fg=COLORS["blue_dark"],
                 font=("Microsoft YaHei", 8), wraplength=285, justify="left").pack(
            anchor="w", padx=18, pady=(0, 8))
        table = tk.Frame(left, bg=COLORS["surface"])
        table.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        self.file_listbox = create_file_table(table, [
            ("type", "类型", 82, "center", False),
            ("name", "文件名", 132, "w", True),
            ("status", "状态", 68, "center", False),
        ])

    def _build_dashboard_features(self):
        self.canvas = tk.Canvas(self.frame, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        content = tk.Frame(self.canvas, bg=COLORS["bg"])
        window = self.canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        scrollbar.grid(row=0, column=2, sticky="ns")
        groups = [
            ("总体分析", "▥", "blue", [
                ("预警刹车类别", "各类预警刹车统计", self.show_type_chart, "▦", "blue"),
                ("单位 Top10", "预警刹车责任单位排行", self.show_unit_top10, "▥", "blue"),
                ("问题类别 Top10", "预警问题类别排行", self.show_category_chart, "☷", "blue"),
                ("总体趋势", "预警刹车周期趋势分析", self.show_overall_weekly_trend, "⌁", "blue")]),
            ("单位预警刹车画像", "♟", "green", [
                ("单位问题类别 Top3", "单位预警问题类别排行", self.open_unit_problem_category_top3_selection, "③", "green"),
                ("单位趋势", "单位预警刹车周期趋势", self.open_unit_trend_selection, "⌁", "green")]),
            ("预警刹车专项分析", "◆", "orange", [
                ("专项趋势", "问题类别周期变化趋势", self.open_special_trend_category_selection,
                 "⌁", "orange"),
                ("专项分析（单位）", "问题类别单位周期趋势", self.open_special_category_selection,
                 "▦", "orange")])]
        self.analysis_cards = build_dashboard_sections(content, groups, columns=4)

    def set_busy(self, busy, loading=False):
        # Preserve the file panel appearance during short analysis tasks; the
        # command handlers below still enforce the global task lock.
        state = "disabled" if loading else "normal"
        for button in self.file_action_buttons:
            if str(button.cget("state")) != state:
                button.configure(state=state)
        for button in self.period_buttons.values():
            if str(button.cget("state")) != state:
                button.configure(state=state)
        for card in self.analysis_cards:
            set_feature_card_enabled(card, not busy)
        cancel_state = "normal" if loading else "disabled"
        if str(self.cancel_button.cget("state")) != cancel_state:
            self.cancel_button.configure(state=cancel_state)

    def update_period_button_styles(self):
        selected = self.period_type.get()
        for value, button in self.period_buttons.items():
            active = value == selected
            button.configure(
                bg=COLORS["blue"] if active else COLORS["blue_soft"],
                fg="white" if active else COLORS["blue_dark"],
                activebackground=COLORS["blue_dark"] if active else "#DCEBFA",
                activeforeground="white" if active else COLORS["blue_dark"]
            )

    def select_period(self, period_type):
        if self._reject_when_busy():
            return
        if period_type == self.period_type.get():
            return
        self.period_type.set(period_type)
        self.state.period_type = period_type
        self.state.invalidate_cache()
        self.update_period_button_styles()
        period_name = self.get_period_name()
        self.progress_text.set(f"当前统计周期：按{period_name}")
        self.app.write_log(f"预警刹车统计周期切换为按{period_name}")

    def get_period_name(self):
        return {"week": "周", "month": "月", "quarter": "季度"}[self.period_type.get()]

    def get_period_xlabel(self):
        return {
            "week": "时间周期（周一至周日）",
            "month": "时间周期（按月）",
            "quarter": "时间周期（按季度）",
        }[self.period_type.get()]

    def create_scroll_window(self, title):
        return create_scrollable_dialog(self.app.root, title, "420x550")

    def _on_mousewheel(self, event):
        try:
            if event.widget.winfo_toplevel() != self.app.root:
                return "break"
        except (AttributeError, tk.TclError):
            return "break"

        self.canvas.update_idletasks()

        content_bbox = self.canvas.bbox("all")

        if not content_bbox:
            return "break"

        content_height = content_bbox[3] - content_bbox[1]
        visible_height = self.canvas.winfo_height()

        # 内容未超出可视区域时始终固定在顶部
        if content_height <= visible_height:
            self.canvas.yview_moveto(0)
            return "break"

        first, last = self.canvas.yview()

        # 已在顶部，禁止继续向上滚动
        if event.delta > 0 and first <= 0:
            self.canvas.yview_moveto(0)
            return "break"

        # 已在底部，禁止继续向下滚动
        if event.delta < 0 and last >= 1:
            return "break"

        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def show(self):
        self.frame.pack(fill="both", expand=True)
        # 每次进入预警刹车页面时回到顶部
        self.canvas.yview_moveto(0)
        self.app.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.app.refresh_status()

    def hide(self):
        self.app.root.unbind_all("<MouseWheel>")
        self.frame.pack_forget()

    def refresh_file_listbox(self):
        for item_id in self.file_listbox.get_children():
            self.file_listbox.delete(item_id)
        loader = self.app.analyzer.brake_loader

        for item in loader.get_files():
            status = item["status"] + (f" {item['rows']}条" if item["rows"] else "")
            self.file_listbox.insert("", "end", values=(item["预警刹车类型"], item["name"], status))

        counts = loader.get_type_file_counts()
        summary = "    ".join(
            f"{brake_type}：{counts[brake_type]}个"
            for brake_type in self.BRAKE_TYPES
        )
        self.type_summary_var.set(f"已识别文件    {summary}")
        self.app.refresh_status()

    def add_files(self):
        if self._reject_when_busy():
            return
        paths = filedialog.askopenfilenames(
            title="上传预警刹车Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls")]
        )
        if not paths:
            return

        loader = self.app.analyzer.brake_loader

        def worker(_report, cancel_event):
            return loader.add_files(list(paths), cancel_event)

        def success(result):
            added, skipped = result
            self.invalidate_data()
            self.refresh_file_listbox()
            self.progress_text.set(f"已新增{added}个文件，类型识别完成")
            if skipped:
                messagebox.showinfo("重复文件已跳过", "\n".join(skipped))

        def failed(exc, details, cancelled=False):
            self.progress_text.set("文件识别已取消" if cancelled else "文件识别失败")
            if cancelled:
                self.app.write_log("预警刹车文件识别已取消")
            else:
                self.app.report_error("预警刹车文件识别", exc, details)
                messagebox.showerror("文件识别失败", str(exc).splitlines()[0])

        self.app.submit_task("预警刹车文件识别", worker, success, failed,
                             kind="loading")

    def remove_selected_file(self):
        if self._reject_when_busy():
            return
        selected = self.file_listbox.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择文件")
            return
        self.app.analyzer.brake_loader.remove_file(self.file_listbox.index(selected[0]))
        self.invalidate_data()
        self.refresh_file_listbox()

    def clear_all_files(self):
        if self._reject_when_busy():
            return
        if messagebox.askyesno("确认", "确定清空全部预警刹车文件吗？"):
            self.app.analyzer.brake_loader.clear()
            self.invalidate_data()
            self.refresh_file_listbox()

    def invalidate_data(self):
        self.state.invalidate()
        self.progress_var.set(0)
        self.progress_text.set("文件已变更，请重新加载")
        self.app.refresh_status()

    def update_progress(self, current, total, item):
        self.progress_var.set(current / total * 100)
        self.progress_text.set(f"正在加载：{item['预警刹车类型']} / {item['name']}")

    def load_data(self):
        if self._reject_when_busy():
            return
        loader = self.app.analyzer.brake_loader
        if loader.get_total_file_count() == 0:
            messagebox.showwarning("提示", "请先添加Excel文件")
            return
        def worker(report, cancel_event):
            df_all, df_list = loader.load(report, cancel_event)
            raw_counts = df_all["预警刹车类型"].value_counts().to_dict()
            valid_counts = self.app.analyzer.brake.type_counts(df_all)
            return df_all, df_list, raw_counts, valid_counts

        def success(result):
            df_all, df_list, raw_counts, valid_counts = result
            self.state.set_loaded(df_all, df_list)
            self.progress_var.set(100)
            self.progress_text.set(
                f"加载完成：{loader.get_total_file_count()}个文件，共{len(df_all)}条"
            )
            self.refresh_file_listbox()
            valid_total = sum(valid_counts.values())
            summary = "\n".join(
                f"{name}：导入{raw_counts.get(name, 0)}条，有效{valid_counts.get(name, 0)}条"
                for name in self.BRAKE_TYPES
            )
            messagebox.showinfo(
                "加载完成", f"{summary}\n\n有效数据：{valid_total}条\n原始加载：{len(df_all)}条"
            )
            self.app.write_log("预警刹车数据加载完成：")
            for name in self.BRAKE_TYPES:
                self.app.write_log(
                    f"  {name}：导入{raw_counts.get(name, 0)}条，有效{valid_counts.get(name, 0)}条"
                )
            self.app.write_log(f"  合计：导入{len(df_all)}条，有效{valid_total}条")

        def failed(exc, details, cancelled=False):
            self.progress_text.set("加载已取消" if cancelled else "数据加载失败")
            self.refresh_file_listbox()
            if cancelled:
                self.app.write_log("预警刹车数据加载已取消，未更新分析数据")
            else:
                self.app.report_error("预警刹车数据加载", exc, details)
                messagebox.showerror("加载失败", str(exc).splitlines()[0])

        self.app.submit_task("预警刹车数据", worker, success, failed,
                             self.update_progress, kind="loading")

    def _reject_when_busy(self):
        runner = getattr(self.app, "task_runner", None)
        if runner is not None and runner.busy:
            self.app.write_log(f"操作未执行：当前正在执行{runner.current_name}")
            return True
        return False
