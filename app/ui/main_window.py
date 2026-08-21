import tkinter as tk
import ctypes
import ctypes.wintypes
import logging
import os
from logging.handlers import RotatingFileHandler
from tkinter import scrolledtext
from datetime import datetime

from app.core.hazard.hazard_config import HazardConfig
from app.core.analyzer import Analyzer
from app.core.analysis_state import AnalysisState
from app.core.background_task import BackgroundTaskRunner
from app.charts.font_config import init_matplotlib_font
from app.ui.pages.hazard_page import HazardPage
from app.ui.pages.brake_page import BrakePage
from app.ui.pages.risk_page import RiskPage
from app.ui.theme import COLORS, FONTS, configure_styles, panel


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("HSE数据分析平台")
        self.configure_initial_window()
        configure_styles(root)

        self.cfg = HazardConfig()
        self.analyzer = Analyzer(self.cfg)
        self.hazard_state = AnalysisState()
        self.brake_state = AnalysisState()
        self.current_module = "隐患分析"
        self.nav_buttons = {}
        self._configure_error_log()

        self.create_header()
        self.main_area = tk.Frame(root, bg=COLORS["bg"])
        self.main_area.pack(fill="both", expand=True, padx=20, pady=(14, 8))
        self.page_container = tk.Frame(self.main_area, bg=COLORS["bg"])
        self.page_container.pack(fill="both", expand=True)

        self.hazard_page = HazardPage(self.page_container, self)
        self.brake_page = BrakePage(self.page_container, self)
        self.risk_page = RiskPage(self.page_container, self)

        self.task_runner = BackgroundTaskRunner(root, self._on_task_state)

        self.create_log()
        self.create_statusbar()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.show_hazard()
        self.update_clock()

    def configure_initial_window(self):
        """根据当前屏幕生成适合仪表盘的居中初始窗口。"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 优先使用Windows工作区尺寸，自动避开任务栏。
        work_x = 0
        work_y = 0
        work_width = screen_width
        work_height = screen_height
        try:
            rect = ctypes.wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                work_x = rect.left
                work_y = rect.top
                work_width = rect.right - rect.left
                work_height = rect.bottom - rect.top
        except (AttributeError, OSError):
            pass

        width = min(1600, max(1200, int(work_width * 0.90)))
        # 尽量占满工作区高度，为底部完整日志区预留空间。
        height = max(760, work_height - 225)

        # 小屏幕不能强行使用最小推荐值，避免窗口超出桌面。
        width = min(width, work_width)
        height = min(height, work_height)
        x = work_x + max(0, (work_width - width) // 2)
        y = work_y + max(0, (work_height - height) // 2)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(min(1100, screen_width), min(700, screen_height))

    def create_header(self):
        header = tk.Frame(self.root, bg=COLORS["surface"], height=92,
                          highlightthickness=1, highlightbackground=COLORS["border"])
        header.pack(fill="x")
        header.pack_propagate(False)
        brand = tk.Frame(header, bg=COLORS["surface"])
        brand.pack(side="left", fill="y", padx=(34, 25))
        self.create_brand_icon(brand).pack(side="left", padx=(0, 14), pady=13)
        names = tk.Frame(brand, bg=COLORS["surface"])
        names.pack(side="left", pady=16)
        tk.Label(names, text="HSE数据分析平台", bg=COLORS["surface"], fg=COLORS["blue_dark"],
                 font=FONTS["brand"]).pack(anchor="w")
        tk.Label(names, text="工程建设安全数据分析与风险预警", bg=COLORS["surface"],
                 fg=COLORS["muted"], font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(3, 0))

        nav = tk.Frame(header, bg=COLORS["surface"])
        nav.pack(side="left", fill="y", padx=(8, 0))
        specs = [("隐患分析", "▤", self.show_hazard),
                 ("预警刹车分析", "♟", self.show_brake),
                 ("综合分析", "◔", self.show_risk)]
        for name, icon, command in specs:
            btn = tk.Button(nav, text=f"{icon}  {name}", command=command, relief="flat",
                            borderwidth=0, width=18, cursor="hand2",
                            font=FONTS["nav"])
            btn.pack(side="left", fill="y", padx=2)
            self.nav_buttons[name] = btn

    def create_brand_icon(self, parent):
        """绘制不依赖字体资源的盾牌数据分析标志。"""
        canvas = tk.Canvas(parent, width=58, height=64, bg=COLORS["surface"],
                           highlightthickness=0, borderwidth=0)
        # 盾牌外轮廓
        shield = [29, 4, 52, 13, 49, 39, 43, 49, 29, 59,
                  15, 49, 9, 39, 6, 13]
        canvas.create_polygon(shield, fill="#F2F8FE", outline=COLORS["blue"],
                              width=3, smooth=True)
        # 数据柱与上升趋势线
        canvas.create_rectangle(17, 32, 21, 43, fill=COLORS["blue"], outline="")
        canvas.create_rectangle(25, 27, 29, 43, fill=COLORS["blue"], outline="")
        canvas.create_rectangle(33, 22, 37, 43, fill=COLORS["blue"], outline="")
        canvas.create_line(16, 30, 26, 24, 35, 17, 42, 20,
                           fill=COLORS["blue_dark"], width=2, smooth=True)
        canvas.create_oval(33, 15, 37, 19, fill=COLORS["blue_dark"], outline="")
        return canvas

    def create_log(self):
        box = panel(self.root)
        box.pack(fill="x", padx=20, pady=(0, 7))
        head = tk.Frame(box, bg=COLORS["surface"])
        head.pack(fill="x", padx=14, pady=(8, 3))
        tk.Label(head, text="▤  运行日志", bg=COLORS["surface"], fg=COLORS["blue_dark"],
                 font=("Microsoft YaHei", 10, "bold")).pack(side="left")
        self.log = scrolledtext.ScrolledText(box, height=5, relief="flat", borderwidth=0,
                                             bg="#FBFCFE", fg="#354A67",
                                             font=("Microsoft YaHei", 9))
        self.log.pack(fill="x", padx=14, pady=(0, 10))

    def create_statusbar(self):
        bar = tk.Frame(self.root, bg="#EDF3F9", height=38,
                       highlightthickness=1, highlightbackground=COLORS["border"])
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.status_module = tk.StringVar()
        self.status_files = tk.StringVar()
        self.status_rows = tk.StringVar()
        self.status_clock = tk.StringVar()
        self.status_task = tk.StringVar(value="")
        for variable in (self.status_module, self.status_files, self.status_rows):
            tk.Label(bar, textvariable=variable, bg="#EDF3F9", fg=COLORS["text"],
                     font=("Microsoft YaHei", 9)).pack(side="left", padx=24)
        tk.Label(bar, textvariable=self.status_task, bg="#EDF3F9", fg=COLORS["blue_dark"],
                 font=("Microsoft YaHei", 9, "bold")).pack(side="left", padx=12)
        tk.Label(bar, text="♙  当前用户：admin", bg="#EDF3F9", fg=COLORS["text"],
                 font=("Microsoft YaHei", 9)).pack(side="right", padx=24)
        tk.Label(bar, textvariable=self.status_clock, bg="#EDF3F9", fg=COLORS["text"],
                 font=("Microsoft YaHei", 9)).pack(side="right", padx=12)

    def write_log(self, msg):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log.insert(tk.END, f"{stamp}    {msg}\n")
        self.log.see(tk.END)

    def _configure_error_log(self):
        os.makedirs("logs", exist_ok=True)
        self.error_logger = logging.getLogger("hse_analyzer")
        self.error_logger.setLevel(logging.ERROR)
        if not self.error_logger.handlers:
            handler = RotatingFileHandler(
                os.path.join("logs", "hse_analyzer.log"),
                maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"
            ))
            self.error_logger.addHandler(handler)

    def report_error(self, context, exc, details=""):
        full = details or f"{type(exc).__name__}: {exc}"
        self.write_log(f"{context}失败：{full}")
        self.error_logger.error("%s失败\n%s", context, full)

    def submit_task(self, name, worker, on_success, on_error,
                    on_progress=None, kind="analyzing"):
        started = self.task_runner.submit(
            name, worker, on_success, on_error, on_progress, kind
        )
        if not started:
            self.write_log(f"任务未启动：当前正在执行{self.task_runner.current_name}")
        return started

    def cancel_loading(self):
        if self.task_runner.cancel_current():
            self.write_log("正在取消加载，将在当前文件读取完成后停止")

    def _on_task_state(self, state, name):
        labels = {
            "idle": "", "loading": f"后台加载：{name}",
            "analyzing": f"后台分析：{name}", "cancelling": f"正在取消：{name}"
        }
        self.status_task.set(labels.get(state, name))
        busy = state != "idle"
        loading = state in {"loading", "cancelling"}
        self.hazard_page.set_busy(busy, loading)
        self.brake_page.set_busy(busy, loading)
        self.risk_page.set_busy(busy, loading)
        if state == "idle" and self.current_module == "综合分析":
            # 用户可在其他模块加载期间切到综合页；任务结束后自动补一次刷新。
            self.root.after(0, self.risk_page.refresh_analysis)

    def run_cached(self, state, operation, args, calculation):
        cached = state.cache_get(operation, *args)
        if cached is not None:
            return cached
        return state.cache_set(operation, calculation(), *args)

    def refresh_status(self):
        if self.current_module == "隐患分析":
            files = self.analyzer.loader.get_total_file_count()
            rows = self.hazard_state.row_count
        elif self.current_module == "预警刹车分析":
            files = self.analyzer.brake_loader.get_total_file_count()
            rows = self.brake_state.row_count
        else:
            files = (
                self.analyzer.loader.get_total_file_count()
                + self.analyzer.brake_loader.get_total_file_count()
            )
            rows = self.hazard_state.row_count + self.brake_state.row_count
        self.status_module.set(f"♙  当前模块：{self.current_module}")
        self.status_files.set(f"▤  已加载文件：{files}个")
        self.status_rows.set(f"↓  数据总量：{rows:,}条")

    def update_clock(self):
        self.status_clock.set("◷  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def hide_all_pages(self):
        self.hazard_page.hide()
        self.brake_page.hide()
        self.risk_page.hide()

    def activate(self, name):
        self.current_module = name
        for key, button in self.nav_buttons.items():
            active = key == name
            button.configure(bg=COLORS["blue"] if active else COLORS["surface"],
                             fg="white" if active else COLORS["text"],
                             activebackground=COLORS["blue_dark"] if active else COLORS["blue_soft"],
                             activeforeground="white" if active else COLORS["text"])
        self.refresh_status()
        self.write_log(f"切换到：{name}")

    def show_hazard(self):
        self.hide_all_pages(); self.hazard_page.show(); self.activate("隐患分析")

    def show_brake(self):
        self.hide_all_pages(); self.brake_page.show(); self.activate("预警刹车分析")

    def show_risk(self):
        self.hide_all_pages(); self.risk_page.show(); self.activate("综合分析")

    def close(self):
        self.task_runner.shutdown()
        self.root.destroy()


def run_app():
    # Windows高DPI感知；旧系统不支持时保持Tk默认行为。
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
    init_matplotlib_font()
    root = tk.Tk()
    try:
        dpi = root.winfo_fpixels("1i")
        root.tk.call("tk", "scaling", dpi / 72.0)
    except tk.TclError:
        pass
    root.option_add("*Font", ("Microsoft YaHei", 11))
    App(root)
    root.mainloop()
