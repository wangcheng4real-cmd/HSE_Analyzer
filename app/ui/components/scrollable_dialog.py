import tkinter as tk


def create_scrollable_dialog(root, title, geometry="420x550"):
    """创建带自适应宽度和滚轮边界控制的通用弹窗。"""
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry(geometry)
    win.resizable(True, True)

    container = tk.Frame(win)
    container.pack(fill="both", expand=True)
    canvas = tk.Canvas(container, highlightthickness=0)
    scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    content = tk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=content, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def update_scroll_region(_event=None):
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        canvas.configure(scrollregion=bbox or (0, 0, 0, 0))
        if not bbox or bbox[3] - bbox[1] <= canvas.winfo_height():
            canvas.yview_moveto(0)

    content.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", lambda event: canvas.itemconfig(window_id, width=event.width))

    def on_mousewheel(event):
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= canvas.winfo_height():
            canvas.yview_moveto(0)
            return "break"
        first, last = canvas.yview()
        if event.delta > 0 and first <= 0:
            return "break"
        if event.delta < 0 and last >= 1:
            return "break"
        canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    win.bind("<MouseWheel>", on_mousewheel)
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    return win, content
