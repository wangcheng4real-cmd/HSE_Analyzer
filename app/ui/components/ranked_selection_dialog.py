import tkinter as tk
from tkinter import ttk

from app.ui.theme import COLORS


def sort_ranked_items(item_counts):
    return sorted(
        ((str(name), int(count)) for name, count in item_counts.items()),
        key=lambda item: (-item[1], item[0])
    )


def filter_ranked_items(items, query):
    keyword = query.strip().casefold()
    if not keyword:
        return list(items)
    return [item for item in items if keyword in item[0].casefold()]


class RankedSelectionDialog:
    ITEM_ICONS = {
        "单位": "▥",
        "区域": "⌾",
        "分类": "▦",
    }

    def __init__(
        self, parent, title, item_kind, item_counts, on_confirm,
        count_label="隐患数量", common_items=None
    ):
        self.parent = parent
        self.item_kind = item_kind
        self.on_confirm = on_confirm
        self.items = sort_ranked_items(item_counts)
        self.common_items = list(common_items or [])
        if self.common_items:
            count_map = dict(self.items)
            self.filtered_items = sorted(
                (
                    (name, int(count_map.get(name, 0)))
                    for name in self.common_items
                ),
                key=lambda item: (-item[1], item[0])
            )
            common_names = set(self.common_items)
            self.other_items = [
                item for item in self.items if item[0] not in common_names
            ]
        else:
            self.filtered_items = list(self.items)
            self.other_items = []
        self.selected_name = self.filtered_items[0][0] if self.filtered_items else None
        self.card_widgets = {}

        self.window = tk.Toplevel(parent)
        # Build the complete dialog off-screen.  A Toplevel becomes visible as
        # soon as it is created on Windows; laying it out while visible causes
        # a small default window to flash before the final geometry is applied.
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.title(title)
        self.window.configure(bg=COLORS["surface"], borderwidth=1, relief="solid")
        self.window.minsize(480, 560)
        self.window.transient(parent)

        self._build_header(title)
        self._build_search()
        self._build_summary(count_label)
        # Reserve the footer before packing the expanding list.  Otherwise the
        # common-category selector can consume the full height and push the
        # confirmation buttons outside the visible window.
        self._build_footer()
        self._build_list()
        self._render_items()

        self.window.bind("<Escape>", lambda _event: self.close())
        self.window.bind("<Return>", lambda _event: self.confirm())
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.update_idletasks()
        self.window.geometry(self._center_geometry(560, 720))
        transparent = False
        try:
            self.window.attributes("-alpha", 0.0)
            transparent = True
        except tk.TclError:
            pass
        self.window.deiconify()
        # A withdrawn Toplevel is not fully laid out by Windows.  Map it while
        # transparent, let Tk paint all child cards, then reveal the completed
        # dialog in one frame instead of showing a blank shell first.
        self.window.update_idletasks()
        self.window.update()
        if transparent:
            self.window.attributes("-alpha", 1.0)
        self.window.lift()
        self._schedule_focus()

    def _center_geometry(self, width, height):
        self.parent.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = max(self.parent.winfo_width(), width)
        parent_height = max(self.parent.winfo_height(), height)
        x = parent_x + max(0, (parent_width - width) // 2)
        y = parent_y + max(0, (parent_height - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _build_header(self, title):
        header = tk.Frame(self.window, bg=COLORS["surface"])
        header.pack(fill="x", padx=24, pady=(20, 12))
        icon = self.ITEM_ICONS.get(self.item_kind, "▦")
        icon_label = tk.Label(
            header, text=icon, bg=COLORS["surface"], fg=COLORS["blue"],
            font=("Microsoft YaHei", 17, "bold"), cursor="fleur"
        )
        icon_label.pack(side="left")
        title_label = tk.Label(
            header, text=title, bg=COLORS["surface"], fg=COLORS["text"],
            font=("Microsoft YaHei", 15, "bold"), cursor="fleur"
        )
        title_label.pack(side="left", padx=10)
        close_button = tk.Button(
            header, text="×", command=self.close, relief="flat", borderwidth=0,
            bg=COLORS["surface"], activebackground=COLORS["blue_soft"],
            fg=COLORS["text"], activeforeground=COLORS["blue_dark"],
            font=("Microsoft YaHei", 18), cursor="hand2", padx=5
        )
        close_button.pack(side="right")
        for widget in (header, icon_label, title_label):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag_window)

    def _start_drag(self, event):
        self._drag_x = event.x_root - self.window.winfo_x()
        self._drag_y = event.y_root - self.window.winfo_y()

    def _drag_window(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.window.geometry(f"+{x}+{y}")

    def _build_search(self):
        if self.common_items:
            self._build_other_selector()
            return
        self.search_box = tk.Frame(
            self.window, bg=COLORS["surface"], highlightthickness=1,
            highlightbackground=COLORS["border"]
        )
        self.search_box.pack(fill="x", padx=24, pady=(4, 14), ipady=5)
        tk.Label(self.search_box, text="⌕", bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("Microsoft YaHei", 17)).pack(side="left", padx=(12, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            self.search_box, textvariable=self.search_var, relief="flat", borderwidth=0,
            bg=COLORS["surface"], fg=COLORS["text"], insertbackground=COLORS["blue"],
            font=("Microsoft YaHei", 11)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=6)
        self.search_entry.insert(0, f"搜索{self.item_kind}名称")
        self.search_entry.configure(fg="#A4B1C2")
        self.search_entry.bind("<FocusIn>", self._focus_search)
        self.search_entry.bind("<FocusOut>", self._blur_search)
        self.search_entry.bind("<ButtonPress-1>", self._activate_search)
        self._suppress_search_trace = False
        self.search_var.trace_add("write", self._on_search)

    def _schedule_focus(self):
        # Schedule exactly one focus hand-off.  Binding focus work to <Map>
        # causes every child card to enqueue another callback on Tk/Windows.
        self._focus_after_id = self.window.after(60, self._focus_dialog)

    def _focus_dialog(self):
        self._focus_after_id = None
        if not self.window.winfo_exists():
            return
        try:
            # The window has already been lifted before it is shown.  Forcing
            # another lift/activation here makes Windows repaint the entire
            # dialog once, which appears as a flash.
            self.window.focus_set()
            if hasattr(self, "search_entry"):
                self.search_entry.focus_set()
        except tk.TclError:
            pass

    def _activate_search(self, _event=None):
        if self.window.winfo_exists():
            try:
                self.window.focus_force()
                self.search_entry.after_idle(self.search_entry.focus_force)
            except tk.TclError:
                pass

    def _build_other_selector(self):
        box = tk.Frame(
            self.window, bg=COLORS["blue_soft"], highlightthickness=1,
            highlightbackground=COLORS["border"]
        )
        box.pack(fill="x", padx=24, pady=(4, 14), ipady=8)
        tk.Label(
            box, text="其他隐患类型", bg=COLORS["blue_soft"],
            fg=COLORS["text"], font=("Microsoft YaHei", 10, "bold")
        ).pack(anchor="w", padx=12, pady=(2, 6))
        subtitle = (f"共 {len(self.other_items)} 个其他分类，按隐患数量从高到低排列"
                    if self.other_items else "当前没有其他隐患分类")
        tk.Label(
            box, text=subtitle, bg=COLORS["blue_soft"], fg=COLORS["muted"],
            font=("Microsoft YaHei", 9)
        ).pack(anchor="w", padx=12, pady=(0, 8))
        style = ttk.Style(self.window)
        style.configure(
            "HSE.Other.TCombobox",
            fieldbackground=COLORS["surface"], background=COLORS["blue"],
            foreground=COLORS["text"], arrowcolor=COLORS["blue_dark"],
            bordercolor=COLORS["blue"], lightcolor=COLORS["blue"],
            darkcolor=COLORS["blue"], padding=8,
            font=("Microsoft YaHei", 10, "bold")
        )
        style.map(
            "HSE.Other.TCombobox",
            fieldbackground=[("readonly", COLORS["surface"])],
            foreground=[("readonly", COLORS["text"])],
            selectbackground=[("readonly", COLORS["surface"])],
            selectforeground=[("readonly", COLORS["text"])],
        )
        self.window.option_add("*TCombobox*Listbox.font", ("Microsoft YaHei", 10))
        self.window.option_add("*TCombobox*Listbox.background", COLORS["surface"])
        self.window.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.window.option_add("*TCombobox*Listbox.selectBackground", COLORS["blue"])
        self.window.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.other_display_map = {
            f"{name}（{count}条）": name for name, count in self.other_items
        }
        self.other_selector_var = tk.StringVar(value="请选择其他隐患分类")
        self.other_selector = ttk.Combobox(
            box, textvariable=self.other_selector_var,
            values=list(self.other_display_map), state="readonly",
            style="HSE.Other.TCombobox", font=("Microsoft YaHei", 10, "bold")
        )
        self.other_selector.pack(fill="x", padx=12, pady=(0, 5), ipady=3)
        self.other_selector.bind("<<ComboboxSelected>>", self._on_other_selected)
        if not self.other_items:
            self.other_selector.configure(state="disabled")

    def _on_other_selected(self, _event=None):
        name = self.other_display_map.get(self.other_selector_var.get())
        if name:
            self._select_other(name)

    def _select_other(self, name):
        previous = self.selected_name
        self.selected_name = name
        self._apply_card_style(previous, False)
        self.confirm_button.configure(state="normal")

    def _focus_search(self, _event=None):
        self.search_box.configure(highlightbackground=COLORS["blue"])
        if self.search_entry.get() == f"搜索{self.item_kind}名称":
            self._suppress_search_trace = True
            try:
                self.search_entry.delete(0, tk.END)
            finally:
                self._suppress_search_trace = False
            self.search_entry.configure(fg=COLORS["text"])

    def _blur_search(self, _event=None):
        self.search_box.configure(highlightbackground=COLORS["border"])
        if not self.search_entry.get():
            self._suppress_search_trace = True
            try:
                self.search_entry.insert(0, f"搜索{self.item_kind}名称")
            finally:
                self._suppress_search_trace = False
            self.search_entry.configure(fg="#A4B1C2")

    def _build_summary(self, count_label):
        summary = tk.Frame(self.window, bg=COLORS["surface"])
        summary.pack(fill="x", padx=24, pady=(0, 8))
        self.count_var = tk.StringVar()
        tk.Label(summary, textvariable=self.count_var, bg=COLORS["surface"],
                 fg=COLORS["muted"], font=("Microsoft YaHei", 10)).pack(side="left")
        if not self.common_items:
            tk.Label(summary, text=f"按{count_label}排序 ↓", bg=COLORS["surface"],
                     fg=COLORS["blue"], font=("Microsoft YaHei", 10, "bold")).pack(side="right")

    def _build_list(self):
        shell = tk.Frame(self.window, bg=COLORS["surface"])
        shell.pack(fill="both", expand=True, padx=(24, 14), pady=(0, 10))
        self.canvas = tk.Canvas(shell, bg=COLORS["surface"], highlightthickness=0)
        scrollbar = tk.Scrollbar(shell, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.canvas, bg=COLORS["surface"])
        self.window_id = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.list_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfig(self.window_id, width=event.width))
        self.window.bind("<MouseWheel>", self._on_mousewheel)

    def _build_footer(self):
        footer = tk.Frame(self.window, bg=COLORS["surface"], highlightthickness=1,
                          highlightbackground=COLORS["border"])
        footer.pack(fill="x", side="bottom")
        buttons = tk.Frame(footer, bg=COLORS["surface"])
        buttons.pack(side="right", padx=24, pady=16)
        tk.Button(buttons, text="取消", command=self.close, width=10, relief="flat",
                  bg="white", fg=COLORS["text"], activebackground=COLORS["blue_soft"],
                  highlightthickness=1, highlightbackground=COLORS["border"],
                  font=("Microsoft YaHei", 11), pady=8, cursor="hand2").pack(side="left", padx=6)
        self.confirm_button = tk.Button(
            buttons, text="确定", command=self.confirm, width=10, relief="flat",
            bg=COLORS["blue"], fg="white", activebackground=COLORS["blue_dark"],
            activeforeground="white", disabledforeground="#D5DCE5",
            font=("Microsoft YaHei", 11, "bold"), pady=8, cursor="hand2"
        )
        self.confirm_button.pack(side="left", padx=6)

    def _on_search(self, *_args):
        if getattr(self, "_suppress_search_trace", False):
            return
        if not hasattr(self, "list_frame"):
            return
        text = self.search_var.get()
        if text == f"搜索{self.item_kind}名称":
            text = ""
        self.filtered_items = filter_ranked_items(self.items, text)
        names = {name for name, _count in self.filtered_items}
        if self.selected_name not in names:
            self.selected_name = self.filtered_items[0][0] if self.filtered_items else None
        self._render_items()

    def _render_items(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.card_widgets.clear()
        if self.common_items:
            self.count_var.set("常用分类")
        else:
            self.count_var.set(f"共 {len(self.filtered_items)} 个{self.item_kind}")
        self.confirm_button.configure(state="normal" if self.selected_name else "disabled")
        if not self.filtered_items:
            tk.Label(self.list_frame, text=f"未找到匹配的{self.item_kind}",
                     bg=COLORS["surface"], fg=COLORS["muted"],
                     font=("Microsoft YaHei", 11)).pack(pady=80)
            return
        for name, count in self.filtered_items:
            self._create_card(name, count)
        self.window.after_idle(self._update_scroll_region)

    def _create_card(self, name, count):
        selected = name == self.selected_name
        bg = "#EDF6FF" if selected else COLORS["surface"]
        border = COLORS["blue"] if selected else COLORS["border"]
        card = tk.Frame(self.list_frame, bg=bg, highlightthickness=1,
                        highlightbackground=border, cursor="hand2")
        card.pack(fill="x", padx=4, pady=5, ipady=5)
        icon_bg = "#DCEEFF" if selected else COLORS["blue_soft"]
        icon = self.ITEM_ICONS.get(self.item_kind, "▦")
        icon_label = tk.Label(card, text=icon, bg=icon_bg, fg=COLORS["blue"],
                              font=("Microsoft YaHei", 12, "bold"), padx=8, pady=6,
                              cursor="hand2")
        icon_label.pack(side="left", padx=(10, 12), pady=7)
        name_label = tk.Label(card, text=name, bg=bg, fg=COLORS["text"],
                              font=("Microsoft YaHei", 11, "bold"), anchor="w",
                              cursor="hand2")
        name_label.pack(side="left", fill="x", expand=True)
        count_label = tk.Label(card, text=f"{count} 条", bg=bg, fg=COLORS["blue"],
                               font=("Microsoft YaHei", 10, "bold"), cursor="hand2")
        count_label.pack(side="right", padx=14)
        widgets = (card, icon_label, name_label, count_label)
        for widget in widgets:
            widget.bind("<Button-1>", lambda _event, value=name: self.select(value))
            widget.bind("<Double-Button-1>", lambda _event, value=name: self.confirm(value))
            widget.bind("<Enter>", lambda _event, value=name: self._hover(value, True))
            widget.bind("<Leave>", lambda _event, value=name: self._hover(value, False))
        self.card_widgets[name] = {
            "card": card,
            "icon": icon_label,
            "name": name_label,
            "count": count_label,
        }

    def _hover(self, name, entering):
        if name == self.selected_name or name not in self.card_widgets:
            return
        widgets = self.card_widgets[name]
        bg = "#F5F9FD" if entering else COLORS["surface"]
        widgets["card"].configure(bg=bg)
        widgets["name"].configure(bg=bg)
        widgets["count"].configure(bg=bg)

    def _apply_card_style(self, name, selected):
        widgets = self.card_widgets.get(name)
        if not widgets:
            return
        bg = "#EDF6FF" if selected else COLORS["surface"]
        border = COLORS["blue"] if selected else COLORS["border"]
        icon_bg = "#DCEEFF" if selected else COLORS["blue_soft"]
        widgets["card"].configure(bg=bg, highlightbackground=border)
        widgets["icon"].configure(bg=icon_bg)
        widgets["name"].configure(bg=bg)
        widgets["count"].configure(bg=bg)

    def select(self, name):
        if name == self.selected_name:
            return
        previous = self.selected_name
        self.selected_name = name
        self._apply_card_style(previous, False)
        self._apply_card_style(name, True)
        if self.common_items:
            self.other_selector_var.set("请选择其他隐患分类")
        self.confirm_button.configure(state="normal")

    def confirm(self, name=None):
        selected = name or self.selected_name
        if not selected:
            return
        callback = self.on_confirm
        self.close()
        callback(selected)

    def _update_scroll_region(self, _event=None):
        if not self.canvas.winfo_exists():
            return
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=bbox or (0, 0, 0, 0))
        if not bbox or bbox[3] - bbox[1] <= self.canvas.winfo_height():
            self.canvas.yview_moveto(0)

    def _on_mousewheel(self, event):
        bbox = self.canvas.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= self.canvas.winfo_height():
            return "break"
        first, last = self.canvas.yview()
        if event.delta > 0 and first <= 0:
            return "break"
        if event.delta < 0 and last >= 1:
            return "break"
        self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def close(self):
        if self.window.winfo_exists():
            focus_after_id = getattr(self, "_focus_after_id", None)
            if focus_after_id:
                try:
                    self.window.after_cancel(focus_after_id)
                except tk.TclError:
                    pass
                self._focus_after_id = None
            self.window.unbind("<MouseWheel>")
            self.window.destroy()
            try:
                if self.parent.winfo_exists():
                    self.parent.after_idle(self.parent.focus_force)
            except tk.TclError:
                pass
