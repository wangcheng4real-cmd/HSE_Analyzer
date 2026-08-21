import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from app.charts.chart import ChartFactory


class ChartWindow:
    @staticmethod
    def _unit_category_options(item):
        """按结果对象的最终清单构造详情下拉框，不做二次归因或排序。"""
        series_by_name = {
            str(name): list(values) for name, values in item.category_series
        }
        ordered = [
            (name, series_by_name[name])
            for name in item.related_category_names
            if name in series_by_name
        ]
        category_map = {name: values for name, values in ordered}
        display_map = {
            f"{name}（累计{sum(values)}条）": name
            for name, values in ordered
        }
        return category_map, display_map, list(display_map)

    @staticmethod
    def _unit_explanation_text(item):
        """详情说明与点击前单位卡片使用同一结果对象文案。"""
        return item.detail_summary

    @staticmethod
    def show(parent, figure, title="数据图表"):
        window = tk.Toplevel(parent)
        # Toplevels are visible immediately on Windows.  Keep the chart hidden
        # until geometry, toolbar, canvas layout and the first draw are ready,
        # otherwise users see the default window followed by a second resize.
        window.withdraw()
        window.title(title or "数据图表")
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        width = min(1280, max(1000, int(screen_width * 0.80)))
        height = min(820, max(700, int(screen_height * 0.76)))
        width = min(width, screen_width - 40)
        height = min(height, screen_height - 80)
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(760, 520)

        canvas = FigureCanvasTkAgg(figure, master=window)
        toolbar = NavigationToolbar2Tk(canvas, window, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="bottom", fill="x")
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # A withdrawn window reports a 1x1 canvas on Windows.  Map it fully
        # transparent first so Tk calculates the real packed widget size, draw
        # against that size, and only then make it visible.  This avoids both
        # the initial flash and the clipped first render.
        transparent = False
        try:
            window.attributes("-alpha", 0.0)
            transparent = True
        except tk.TclError:
            pass
        window.deiconify()
        window.update_idletasks()
        window.update()
        widget = canvas.get_tk_widget()
        width_px = max(1, widget.winfo_width())
        height_px = max(1, widget.winfo_height())
        canvas.resize(SimpleNamespace(width=width_px, height=height_px))
        canvas.draw()
        if transparent:
            window.attributes("-alpha", 1.0)
        window.lift()
        try:
            window.focus_force()
        except tk.TclError:
            pass

        def close():
            figure.clear()
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", close)
        return window

    @staticmethod
    def show_unit_risk_detail(parent, item, title="单位预警详情", xlabel="", ylabel=""):
        category_map, display_map, displays = ChartWindow._unit_category_options(item)
        initial_name = display_map[displays[0]] if displays else ""
        initial_values = category_map.get(initial_name, [])
        empty_category_message = item.related_category_summary()
        figure = ChartFactory.unit_risk_detail(
            list(item.periods), list(item.counts),
            initial_name, initial_values, title=title, xlabel=xlabel, ylabel=ylabel,
            empty_category_message=empty_category_message,
        )

        window = tk.Toplevel(parent)
        window.withdraw()
        window.title(title or "单位预警详情")
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        width = min(1280, max(1000, int(screen_width * 0.82)), screen_width - 40)
        height = min(900, max(740, int(screen_height * 0.82)), screen_height - 70)
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(820, 620)

        selector = tk.Frame(window, bg="#F7FAFD", padx=16, pady=9)
        selector.pack(side="top", fill="x")
        tk.Label(selector, text="二级隐患类别：", bg="#F7FAFD",
                 font=("Microsoft YaHei", 10, "bold")).pack(side="left")
        selected = tk.StringVar(
            value=displays[0] if displays else empty_category_message
        )
        combobox = ttk.Combobox(
            selector, textvariable=selected, values=displays, state="readonly",
            width=42, font=("Microsoft YaHei", 10),
        )
        combobox.pack(side="left", padx=(6, 0))
        if not displays:
            combobox.configure(state="disabled")

        explanation_box = tk.Frame(
            window, bg="#F7FAFD", padx=16, pady=0
        )
        explanation_box.pack(side="top", fill="x", pady=(0, 9))
        explanation_title = tk.Label(
            explanation_box, text="当前预警说明", bg="#F7FAFD", fg="#173B63",
            font=("Microsoft YaHei", 10, "bold"), anchor="w",
        )
        explanation_title.pack(fill="x", pady=(0, 4))
        explanation_body = tk.Frame(explanation_box, bg="#D6E2EE")
        explanation_body.pack(fill="x")
        explanation_scrollbar = ttk.Scrollbar(
            explanation_body, orient="vertical"
        )
        explanation_scrollbar.pack(side="right", fill="y")
        explanation = tk.Text(
            explanation_body, height=6, wrap="word", relief="flat", bd=0,
            bg="#FFFFFF", fg="#334A62", font=("Microsoft YaHei", 9),
            padx=10, pady=7, cursor="arrow",
            yscrollcommand=explanation_scrollbar.set,
        )
        explanation.pack(side="left", fill="x", expand=True, padx=1, pady=1)
        explanation_scrollbar.configure(command=explanation.yview)
        explanation.insert("1.0", ChartWindow._unit_explanation_text(item))
        explanation.configure(state="disabled")

        def scroll_explanation(event):
            if event.delta:
                explanation.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

        for widget in (explanation_box, explanation_title, explanation_body, explanation):
            widget.bind("<MouseWheel>", scroll_explanation)

        canvas = FigureCanvasTkAgg(figure, master=window)
        toolbar = NavigationToolbar2Tk(canvas, window, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="bottom", fill="x")
        canvas.get_tk_widget().pack(fill="both", expand=True)

        def on_selected(_event=None):
            category = display_map.get(selected.get(), "")
            ChartFactory.update_unit_risk_category(
                figure, list(item.periods), category_map.get(category, []), category,
                xlabel=xlabel, ylabel=ylabel,
            )
            canvas.draw_idle()

        combobox.bind("<<ComboboxSelected>>", on_selected)

        transparent = False
        try:
            window.attributes("-alpha", 0.0)
            transparent = True
        except tk.TclError:
            pass
        window.deiconify()
        window.update_idletasks()
        window.update()
        widget = canvas.get_tk_widget()
        canvas.resize(SimpleNamespace(
            width=max(1, widget.winfo_width()), height=max(1, widget.winfo_height())
        ))
        canvas.draw()
        if transparent:
            window.attributes("-alpha", 1.0)
        window.lift()
        try:
            window.focus_force()
        except tk.TclError:
            pass

        def close():
            figure.clear()
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", close)
        window._risk_category_selector = combobox
        window._risk_explanation = explanation
        window._risk_figure = figure
        return window
