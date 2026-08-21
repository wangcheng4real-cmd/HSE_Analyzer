import tkinter as tk
from tkinter import ttk


FONTS = {
    "brand": ("Microsoft YaHei", 20, "bold"),
    "nav": ("Microsoft YaHei", 12, "bold"),
    "section": ("Microsoft YaHei", 13, "bold"),
    "card_title": ("Microsoft YaHei", 11, "bold"),
    "card_subtitle": ("Microsoft YaHei", 9),
    "button": ("Microsoft YaHei", 11, "bold"),
    "body": ("Microsoft YaHei", 10),
    "table": ("Microsoft YaHei", 10),
}


COLORS = {
    "bg": "#F2F6FA",
    "surface": "#FFFFFF",
    "border": "#D9E3EF",
    "text": "#17345F",
    "muted": "#6C7F99",
    "blue": "#0967B9",
    "blue_dark": "#07549A",
    "blue_soft": "#F1F7FD",
    "green": "#2E8B57",
    "green_soft": "#F2F9F4",
    "purple": "#7046A0",
    "purple_soft": "#F7F3FB",
    "orange": "#D66B16",
    "orange_soft": "#FFF7EF",
    "red": "#D83B4C",
}


def configure_styles(root):
    root.configure(bg=COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Treeview", background="white", fieldbackground="white",
                    foreground=COLORS["text"], rowheight=32, borderwidth=0,
                    font=FONTS["table"])
    style.configure("Treeview.Heading", background="#F4F7FB",
                    foreground=COLORS["text"], font=("Microsoft YaHei", 10, "bold"))
    style.map("Treeview", background=[("selected", "#DCEEFF")],
              foreground=[("selected", COLORS["blue_dark"])])
    style.configure("HSE.Horizontal.TProgressbar", troughcolor="#E7EEF6",
                    background=COLORS["green"], borderwidth=0)


def panel(parent, bg=None, **kwargs):
    return tk.Frame(parent, bg=bg or COLORS["surface"], highlightthickness=1,
                    highlightbackground=COLORS["border"], **kwargs)


def section(parent, title, icon="▣", color=None):
    color = color or COLORS["blue"]
    outer = panel(parent)
    head = tk.Frame(outer, bg=COLORS["surface"])
    head.pack(fill="x", padx=16, pady=(12, 6))
    tk.Label(head, text=icon, bg=COLORS["surface"], fg=color,
             font=("Microsoft YaHei", 15, "bold")).pack(side="left")
    tk.Label(head, text=title, bg=COLORS["surface"], fg=COLORS["text"],
             font=FONTS["section"]).pack(side="left", padx=8)
    body = tk.Frame(outer, bg=COLORS["surface"])
    body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
    return outer, body


def action_button(parent, text, command, color, icon=""):
    return tk.Button(parent, text=f"{icon}  {text}" if icon else text,
                     command=command, bg=color, activebackground=color,
                     fg="white", activeforeground="white", relief="flat",
                     cursor="hand2", font=FONTS["button"],
                     padx=10, pady=10, borderwidth=0)


def feature_card(parent, title, subtitle, command, icon="▣", theme="blue"):
    color = COLORS[theme]
    soft = COLORS[f"{theme}_soft"]
    card = tk.Frame(parent, bg=soft, highlightthickness=1,
                    highlightbackground=COLORS["border"], cursor="hand2")
    icon_label = tk.Label(card, text=icon, bg=soft, fg=color,
                          font=("Microsoft YaHei", 21, "bold"), cursor="hand2")
    icon_label.pack(side="left", padx=(13, 9), pady=12)
    text = tk.Frame(card, bg=soft, cursor="hand2")
    text.pack(side="left", fill="both", expand=True, pady=10)
    title_label = tk.Label(text, text=title, bg=soft, fg=color,
                           font=FONTS["card_title"], anchor="w",
                           cursor="hand2")
    title_label.pack(fill="x")
    sub_label = tk.Label(text, text=subtitle, bg=soft, fg=COLORS["muted"],
                         font=FONTS["card_subtitle"], anchor="w", cursor="hand2")
    sub_label.pack(fill="x", pady=(3, 0))
    widgets = (card, icon_label, text, title_label, sub_label)
    card._feature_widgets = widgets
    card._feature_command = command
    card._feature_enabled = True
    for widget in widgets:
        widget.bind("<Button-1>", lambda _event, c=card: (
            c._feature_command() if c._feature_enabled else None
        ))
    return card


def set_feature_card_enabled(card, enabled):
    card._feature_enabled = bool(enabled)
    # Do not reconfigure every child widget for short background tasks.  Tk
    # repaints the full dashboard when their cursor option changes, producing
    # a visible flash behind a newly opened dialog.  The click guard above is
    # sufficient to enforce the disabled state.
