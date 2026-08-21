from app.ui.theme import COLORS, section, feature_card


def build_dashboard_sections(parent, groups, columns=4):
    """根据业务卡片声明生成统一仪表盘分组。"""
    result = []
    for title, icon, theme, cards in groups:
        outer, body = section(parent, title, icon, COLORS[theme])
        outer.pack(fill="x", pady=(0, 10))
        for column in range(columns):
            body.grid_columnconfigure(column, weight=1, uniform="dashboard_cards")
        for index, card in enumerate(cards):
            widget = feature_card(body, *card)
            widget.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=5,
                pady=5
            )
            result.append(widget)
    return result
