from tkinter import filedialog, ttk, messagebox
import tkinter as tk

from app.ui.theme import COLORS, panel, action_button, set_feature_card_enabled
from app.ui.controllers.hazard_analysis_controller import HazardAnalysisController
from app.ui.components.scrollable_dialog import create_scrollable_dialog
from app.ui.components.dashboard_panel import build_dashboard_sections
from app.ui.components.file_table import create_file_table


class HazardPage(HazardAnalysisController):
    #鼠标滚轮函数
    def _on_mousewheel(self, event):
        widget = getattr(event, "widget", None)
        if widget is None or not hasattr(
            widget,
            "winfo_toplevel"
        ):
            return "break"

        try:
            event_window = widget.winfo_toplevel()
        except (AttributeError, tk.TclError):
            return "break"

        if event_window != self.app.root:
            return "break"

        # 仅鼠标位于右侧滚动内容区时滚动，左侧文件表保持独立。
        pointer_x = self.app.root.winfo_pointerx()
        pointer_y = self.app.root.winfo_pointery()
        canvas_x = self.canvas.winfo_rootx()
        canvas_y = self.canvas.winfo_rooty()
        inside_canvas = (
            canvas_x <= pointer_x < canvas_x + self.canvas.winfo_width()
            and canvas_y <= pointer_y < canvas_y + self.canvas.winfo_height()
        )
        if not inside_canvas:
            return None

        bbox = self.canvas.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= self.canvas.winfo_height():
            self.canvas.yview_moveto(0)
            return "break"

        first, last = self.canvas.yview()
        if event.delta > 0 and first <= 0:
            return "break"
        if event.delta < 0 and last >= 1:
            return "break"
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        return "break"
    def bind_main_mousewheel(self):

        self.app.root.bind_all(
            "<MouseWheel>",
            self._on_mousewheel
        )


    def unbind_mousewheel(self):

        self.app.root.unbind_all(
            "<MouseWheel>"
        )
    #宽度自适应
    # 创建带滚动条的弹窗
    # 创建带滚动条的弹窗
    def create_scroll_window(self, title):
        return create_scrollable_dialog(self.app.root, title, "360x500")

    # 新版仪表盘布局。保留上方旧构造代码，便于业务方法继续独立演进。
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.period_type = tk.StringVar(value=self.app.hazard_state.period_type)
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
        tk.Label(left, text="▰  数据文件管理", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=18, pady=(16, 12))

        self.file_action_buttons = []
        button = action_button(left, "添加隐患文件（可多选）", self.add_files, COLORS["blue"], "＋")
        button.pack(
            fill="x", padx=18, pady=4)
        self.file_action_buttons.append(button)
        ops = tk.Frame(left, bg=COLORS["surface"])
        ops.pack(fill="x", padx=14, pady=4)
        button = action_button(ops, "删除选中", self.remove_selected_file, "#E88728", "－")
        button.pack(
            side="left", fill="x", expand=True, padx=4)
        self.file_action_buttons.append(button)
        button = action_button(ops, "清空全部", self.clear_data, COLORS["red"], "×")
        button.pack(
            side="left", fill="x", expand=True, padx=4)
        self.file_action_buttons.append(button)
        button = action_button(left, "加载数据", self.load_data, "#31A35B", "⇧")
        button.pack(
            fill="x", padx=18, pady=(4, 8))
        self.file_action_buttons.append(button)
        self.cancel_button = action_button(left, "取消加载", self.app.cancel_loading,
                                           COLORS["muted"], "■")
        self.cancel_button.pack(fill="x", padx=18, pady=(0, 8))
        self.cancel_button.configure(state="disabled")

        tk.Label(left, text="统计周期", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", padx=18, pady=(4, 5))
        period_row = tk.Frame(left, bg=COLORS["surface"])
        period_row.pack(fill="x", padx=18, pady=(0, 10))
        for value, text in (("week", "按周"), ("month", "按月"), ("quarter", "按季度")):
            button = tk.Button(
                period_row, text=text,
                command=lambda selected=value: self.select_period(selected), relief="flat",
                borderwidth=0, cursor="hand2", font=("Microsoft YaHei", 9, "bold"),
                padx=8, pady=7
            )
            button.pack(side="left", fill="x", expand=True, padx=2)
            self.period_buttons[value] = button
        self.update_period_button_styles()

        self.progress_var = tk.DoubleVar()
        self.progress_text = tk.StringVar(value="等待加载数据")
        ttk.Progressbar(left, variable=self.progress_var, maximum=100,
                        style="HSE.Horizontal.TProgressbar").pack(fill="x", padx=18)
        tk.Label(left, textvariable=self.progress_text, bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("Microsoft YaHei", 8)).pack(fill="x", padx=18, pady=(4, 12))

        tk.Label(left, text="当前隐患文件", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", padx=18, pady=(4, 6))
        table_box = tk.Frame(left, bg=COLORS["surface"])
        table_box.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        self.file_listbox = create_file_table(table_box, [
            ("index", "序号", 58, "center", False),
            ("name", "文件名", 150, "w", True),
            ("status", "状态", 78, "center", False),
        ])
        self.file_count_var = tk.StringVar(value="共 0 个文件")
        tk.Label(left, textvariable=self.file_count_var, bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("Microsoft YaHei", 9)).pack(anchor="w", padx=18, pady=(0, 14))

    def _build_dashboard_features(self):
        right_canvas = tk.Canvas(self.frame, bg=COLORS["bg"], highlightthickness=0)
        right_scroll = ttk.Scrollbar(self.frame, orient="vertical", command=right_canvas.yview)
        right = tk.Frame(right_canvas, bg=COLORS["bg"])
        window = right_canvas.create_window((0, 0), window=right, anchor="nw")
        right.bind("<Configure>", lambda _e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.bind("<Configure>", lambda e: right_canvas.itemconfig(window, width=e.width))
        right_canvas.configure(yscrollcommand=right_scroll.set)
        right_canvas.grid(row=0, column=1, sticky="nsew")
        right_scroll.grid(row=0, column=2, sticky="ns")
        self.canvas = right_canvas
        self.window_id = window

        groups = [
            ("总体分析", "▥", "blue", [
                ("隐患等级分析", "A/B/C/D等级统计", self.level_chart, "♢", "blue"),
                ("单位 Top10", "责任单位隐患统计", self.unit_chart, "▥", "blue"),
                ("隐患分类分析", "隐患分类统计（大类）", self.category_main_chart, "▦", "blue"),
                ("隐患细类 Top10", "隐患细类统计", self.category_sub_chart, "☷", "blue"),
                ("区域分析", "区域隐患统计", self.area_chart, "⌾", "blue"),
                ("接口队办分析", "接口队办统计", self.interface_chart, "♟", "blue"),
                ("AB级隐患统计", "AB级隐患分类统计", self.ab_level_chart, "▦", "blue")]),
            ("单位隐患画像", "♟", "green", [
                ("单位隐患类别 Top5", "各单位隐患类别排行", self.unit_category_ui, "⑤", "green"),
                ("单位AB统计", "各单位AB类隐患", self.unit_ab_ui, "▦", "green"),
                ("单位多发班组", "各单位多发班组Top5", self.unit_team_ui, "♟", "green"),
                ("单位验证率", "各单位按期验证率", self.unit_verify_chart, "✓", "green"),
                ("单位趋势", "各单位隐患趋势分析", self.unit_trend_ui, "⌁", "green")]),
            ("区域隐患画像", "⌾", "purple", [
                ("区域隐患类别 Top5", "各区域隐患类别排行", self.area_profile_ui, "♛", "purple"),
                ("区域AB统计", "各区域AB类隐患", self.area_ab_ui, "▦", "purple"),
                ("区域趋势", "各区域隐患趋势分析", self.area_trend_ui, "⌁", "purple")]),
            ("专项分析", "◆", "orange", [
                ("专项隐患趋势", "专项类别周期变化趋势", self.special_trend_category_ui,
                 "⌁", "orange"),
                ("专项隐患（单位）", "专项隐患单位趋势", self.special_unit_category_ui, "♟", "orange"),
                ("专项隐患（区域）", "专项隐患区域趋势", self.special_area_category_ui, "⌾", "orange")]),
            ("趋势分析", "⌁", "blue", [
                ("总体趋势", "隐患总量周期趋势", self.trend_chart, "◫", "blue"),
                ("AB趋势", "AB级隐患周期趋势", self.ab_trend_chart, "▦", "blue")])]
        self.analysis_cards = build_dashboard_sections(right, groups, columns=4)

    def set_busy(self, busy, loading=False):
        # Short analysis tasks must not toggle native button state: Windows
        # repaints the whole file panel and produces a visible flash.  Keep the
        # appearance stable and enforce the lock in the command handlers.
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

    # =========================
    # 页面显示隐藏
    # =========================

    def show(self):

        self.frame.pack(
            fill="both",
            expand=True
        )

        self.app.refresh_status()
        self.bind_main_mousewheel()


    def hide(self):

        self.unbind_mousewheel()

        self.frame.pack_forget()
    # =========================
    # 文件操作
    # =========================

    def refresh_file_listbox(self):
        for item_id in self.file_listbox.get_children():
            self.file_listbox.delete(item_id)

        files = self.app.analyzer.loader.get_file_list()

        loaded = self.app.hazard_state.loaded
        for index, item in enumerate(files, start=1):
            self.file_listbox.insert("", "end", values=(index, item["name"], "已加载" if loaded else "待加载"))
        self.file_count_var.set(f"共 {len(files)} 个文件")
        self.app.refresh_status()


    def write_log(self, msg):
        self.app.write_log(msg)

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
        self.on_period_change()

    def get_period_name(self):
        return {"week": "周", "month": "月", "quarter": "季度"}[self.period_type.get()]

    def get_period_xlabel(self):
        return {
            "week": "时间周期（周一至周日）",
            "month": "时间周期（按月）",
            "quarter": "时间周期（按季度）"
        }[self.period_type.get()]

    def on_period_change(self):
        self.update_period_button_styles()
        if self.app.hazard_state.df_all is None or self.app.hazard_state.df_all.empty:
            self.app.hazard_state.period_type = self.period_type.get()
            self.app.hazard_state.invalidate_cache()
            self.progress_text.set(f"当前统计周期：按{self.get_period_name()}")
            return

        period_type = self.period_type.get()
        previous_period = self.app.hazard_state.period_type
        source = self.app.hazard_state.df_all
        invalid_count = self.app.hazard_state.invalid_row_count

        def success(result):
            df_all, df_list = result
            self.app.hazard_state.period_type = period_type
            self.app.hazard_state.set_loaded(df_all, df_list, invalid_count)
            period_name = self.get_period_name()
            self.progress_text.set(
                f"已切换为按{period_name}统计：{len(df_list)}个{period_name}周期"
            )
            self.write_log(f"统计周期切换为按{period_name}，共{len(df_list)}个周期")
            self.app.refresh_status()

        def failed(exc, details, _cancelled=False):
            self.period_type.set(previous_period)
            self.update_period_button_styles()
            self.app.report_error("统计周期切换", exc, details)
            messagebox.showerror("周期切换失败", str(exc).splitlines()[0])

        started = self.app.submit_task(
            "隐患周期重分组",
            lambda _report, _cancel: self.app.analyzer.loader.group_by_period(source, period_type),
            success, failed, kind="analyzing"
        )
        if not started:
            self.period_type.set(previous_period)
            self.update_period_button_styles()



    def add_files(self):
        if self._reject_when_busy():
            return
        files = filedialog.askopenfilenames(
            title="添加隐患Excel文件",
            filetypes=[
                ("Excel文件","*.xlsx *.xls")
            ]
        )


        if not files:
            return


        added, skipped = self.app.analyzer.loader.add_files(list(files))

        self.invalidate_data()


        self.refresh_file_listbox()


        self.progress_text.set(
            f"已添加{added}个文件"
        )

        if skipped:
            messagebox.showinfo(
                "重复文件已跳过",
                "以下文件已在列表中：\n" + "\n".join(skipped)
            )

    def invalidate_data(self):
        self.app.hazard_state.invalidate()
        self.app.hazard_state.period_type = self.period_type.get()
        self.app.refresh_status()



    def remove_selected_file(self):

        if self._reject_when_busy():
            return

        selected = self.file_listbox.selection()


        if not selected:

            messagebox.showwarning(
                "提示",
                "请选择文件"
            )

            return


        self.app.analyzer.loader.remove_file(
            self.file_listbox.index(selected[0])
        )

        self.invalidate_data()


        self.refresh_file_listbox()



    def clear_data(self):

        if self._reject_when_busy():
            return

        self.app.analyzer.loader.clear()


        self.invalidate_data()


        self.refresh_file_listbox()


        self.progress_text.set(
            "数据已清空"
        )



    def load_data(self):

        if self._reject_when_busy():
            return

        loader = self.app.analyzer.loader

        if loader.get_total_file_count() == 0:

            messagebox.showwarning(
                "提示",
                "请先添加文件"
            )

            return



        period_type = self.period_type.get()

        def worker(report, cancel_event):
            df_all, df_list = loader.load(report, period_type, cancel_event)
            return df_all, df_list, loader.invalid_date_count

        def success(result):
            df_all, df_list, invalid_count = result
            self.app.hazard_state.period_type = period_type
            self.app.hazard_state.set_loaded(df_all, df_list, invalid_count)
            self.refresh_file_listbox()
            self.progress_var.set(100)
            period_name = self.get_period_name()
            self.progress_text.set(
                f"加载完成：{len(df_all)}条有效数据，{len(df_list)}个{period_name}周期"
            )
            self.write_log(
                f"数据加载完成：{loader.get_total_file_count()}个文件，{len(df_all)}条有效数据，"
                f"{len(df_list)}个{period_name}周期，跳过{invalid_count}条无效检查日期记录"
            )

        def failed(exc, details, cancelled=False):
            self.progress_text.set("加载已取消" if cancelled else "数据加载失败")
            if cancelled:
                self.write_log("隐患数据加载已取消，未更新分析数据")
            else:
                self.app.report_error("隐患数据加载", exc, details)
                messagebox.showerror("数据加载失败", str(exc).splitlines()[0])

        self.app.submit_task("隐患数据", worker, success, failed,
                             self.update_progress, kind="loading")

    def _reject_when_busy(self):
        runner = getattr(self.app, "task_runner", None)
        if runner is not None and runner.busy:
            self.write_log(f"操作未执行：当前正在执行{runner.current_name}")
            return True
        return False



    def update_progress(
        self,
        current,
        total,
        filename
    ):


        self.progress_var.set(
            current / total * 100
        )


        self.progress_text.set(
            f"正在读取:{filename}"
        )





    # =========================
    # 总体分析
    # =========================
