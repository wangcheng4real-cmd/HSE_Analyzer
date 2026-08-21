from tkinter import ttk


def create_file_table(parent, columns):
    """创建统一样式的文件Treeview。

    columns: [(key, title, width, anchor, stretch), ...]
    """
    keys = tuple(item[0] for item in columns)
    table = ttk.Treeview(parent, columns=keys, show="headings", selectmode="browse")
    for key, title, width, anchor, stretch in columns:
        table.heading(key, text=title)
        table.column(
            key, width=width, minwidth=width,
            anchor=anchor, stretch=stretch
        )
    table.pack(fill="both", expand=True)
    return table
