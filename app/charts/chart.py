from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib import colormaps
from itertools import cycle
import math
import re
from app.charts.font_config import init_matplotlib_font


init_matplotlib_font()


class ChartFactory:
    """只生成独立Figure，不负责窗口显示。"""

    @staticmethod
    def compact_period_label(value):
        """把完整周期文字压缩为适合横坐标的短标签。"""
        text = str(value)
        week = re.fullmatch(
            r"(\d{4})-(\d{2})-(\d{2})\s*至\s*(\d{4})-(\d{2})-(\d{2})", text
        )
        if week:
            start_year, start_month, start_day, end_year, end_month, end_day = week.groups()
            if start_year == end_year:
                return f"{start_month}/{start_day}–{end_month}/{end_day}"
            return (
                f"{start_year}/{start_month}/{start_day}–"
                f"{end_year}/{end_month}/{end_day}"
            )
        month = re.fullmatch(r"(\d{4})年(\d{2})月", text)
        if month:
            return f"{month.group(1)}-{month.group(2)}"
        quarter = re.fullmatch(r"(\d{4})年第([1-4])季度", text)
        if quarter:
            return f"{quarter.group(1)} Q{quarter.group(2)}"
        return text

    @staticmethod
    def _axis_ticks(values, max_ticks=8):
        """保留全部数据点，只抽样横坐标文字并确保末项可见。"""
        count = len(values)
        if count <= max_ticks:
            indexes = list(range(count))
        else:
            step = math.ceil(count / max_ticks)
            indexes = list(range(0, count, step))
            if indexes[-1] != count - 1:
                indexes.append(count - 1)
        labels = [ChartFactory.compact_period_label(values[index]) for index in indexes]
        rotation = 30 if any(len(label) > 13 for label in labels) else 0
        return indexes, labels, rotation

    @staticmethod
    def bar(x, y, title="", xlabel="", ylabel=""):
        figure = Figure(figsize=(11, 7), dpi=100, constrained_layout=True)
        ax = figure.add_subplot(111)
        indexes = range(len(x))
        bars = ax.bar(indexes, y)
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.set_xticks(list(indexes), x, rotation=45, ha="right")
        max_y = max(y) if len(y) else 0
        ax.set_ylim(bottom=0, top=max_y * 1.15 if max_y else 1)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        for bar_item, value in zip(bars, y):
            ax.text(
                bar_item.get_x() + bar_item.get_width() / 2,
                bar_item.get_height(), str(value),
                ha="center", va="bottom", fontsize=10
            )
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        return figure

    @staticmethod
    def pie(labels, values, title=""):
        figure = Figure(figsize=(11, 7), dpi=100, constrained_layout=True)
        grid = figure.add_gridspec(1, 2, width_ratios=(2.2, 1), wspace=0.08)
        chart_ax = figure.add_subplot(grid[0, 0])
        chart_ax.pie(
            values, labels=labels, autopct="%1.1f%%",
            startangle=90, radius=0.82, labeldistance=1.08,
            pctdistance=0.66, textprops={"fontsize": 10}
        )
        chart_ax.set_title(title, fontsize=14)
        chart_ax.set_aspect("equal")
        text_ax = figure.add_subplot(grid[0, 1])
        text_ax.axis("off")
        lines = ["数量统计", ""] + [
            f"{label} : {value}" for label, value in zip(labels, values)
        ]
        text_ax.text(0, 0.5, "\n".join(lines), fontsize=12, va="center")
        return figure

    @staticmethod
    def line(x, y, title="", xlabel="", ylabel=""):
        figure = Figure(figsize=(11, 7), dpi=100, constrained_layout=True)
        ax = figure.add_subplot(111)
        indexes = range(len(x))
        ax.plot(indexes, y, marker="o", linewidth=2)
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        tick_indexes, tick_labels, rotation = ChartFactory._axis_ticks(x)
        ax.set_xticks(
            tick_indexes, tick_labels, rotation=rotation,
            ha="right" if rotation else "center"
        )
        max_y = max(y) if len(y) else 0
        ax.set_ylim(bottom=0, top=max_y * 1.2 if max_y else 1)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        for index, value in enumerate(y):
            ax.text(index, value, str(value), ha="center", va="bottom", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        return figure

    @staticmethod
    def donut(labels, values, title="", center_label="总数"):
        """适合仪表盘卡片的环形构成图。"""
        figure = Figure(figsize=(6.2, 4.2), dpi=100, constrained_layout=True)
        ax = figure.add_subplot(111)
        total = sum(values)
        if total <= 0:
            ax.axis("off")
            ax.text(0.5, 0.5, "所选时间段内没有数据", ha="center", va="center",
                    color="#6C7F99", fontsize=12, transform=ax.transAxes)
            ax.set_title(title, fontsize=13)
            return figure
        colors = ["#EF5350", "#F5A623", "#5B9FE5", "#45B97C", "#26A6B5"]
        wedges, _ = ax.pie(
            values, startangle=90, counterclock=False, colors=colors[:len(values)],
            wedgeprops={"width": 0.38, "edgecolor": "white"}, radius=0.86,
        )
        legend_labels = [
            f"{label}：{value}条（{value / total * 100:.1f}%）"
            for label, value in zip(labels, values)
        ]
        ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(0.92, 0.5),
                  frameon=False, fontsize=8.5)
        ax.text(0, 0.08, center_label, ha="center", va="center", fontsize=9,
                color="#6C7F99")
        ax.text(0, -0.08, f"{total:,}条", ha="center", va="center", fontsize=15,
                fontweight="bold", color="#17345F")
        ax.set_title(title, fontsize=13, loc="left")
        ax.set_aspect("equal")
        return figure

    @staticmethod
    def multi_line(periods, series, title="", xlabel="", ylabel=""):
        """在同一张图上展示全部单位，并把多列图例放到绘图区下方。"""
        figure = Figure(figsize=(11.5, 6.2), dpi=100, constrained_layout=True)
        ax = figure.add_subplot(111)
        if not periods or not series:
            ax.axis("off")
            ax.text(0.5, 0.5, "所选时间段内没有可统计的数据", ha="center", va="center",
                    color="#6C7F99", fontsize=12, transform=ax.transAxes)
            ax.set_title(title, fontsize=13, loc="left")
            return figure

        palette = list(colormaps["tab20"].colors)
        line_styles = cycle(["-", "--", "-.", ":"])
        indexes = list(range(len(periods)))
        for index, (name, values) in enumerate(series.items()):
            ax.plot(
                indexes, values, label=name, color=palette[index % len(palette)],
                linestyle=next(line_styles), linewidth=1.45, marker="o", markersize=2.8,
            )
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        tick_indexes, tick_labels, rotation = ChartFactory._axis_ticks(periods)
        ax.set_xticks(
            tick_indexes, tick_labels, rotation=rotation,
            ha="right" if rotation else "center", fontsize=8
        )
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        columns = min(5, max(1, len(series)))
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=columns,
                  frameon=False, fontsize=7.5, handlelength=2.4, columnspacing=1.0)
        return figure

    @staticmethod
    def risk_detail(periods, values, history, title="", xlabel="", ylabel=""):
        """风险对象完整趋势与逐周期触发规则明细。"""
        figure = Figure(figsize=(11.5, 7.2), dpi=100, constrained_layout=True)
        grid = figure.add_gridspec(2, 1, height_ratios=(3.2, 1.8))
        ax = figure.add_subplot(grid[0, 0])
        indexes = list(range(len(periods)))
        ax.plot(indexes, values, marker="o", linewidth=2, color="#0967B9")
        tick_indexes, tick_labels, rotation = ChartFactory._axis_ticks(periods)
        ax.set_xticks(tick_indexes, tick_labels, rotation=rotation,
                      ha="right" if rotation else "center")
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        for index, value in enumerate(values):
            ax.text(index, value, str(value), ha="center", va="bottom", fontsize=8)

        detail_ax = figure.add_subplot(grid[1, 0])
        detail_ax.axis("off")
        rows = []
        for item in history[-8:]:
            titles = "、".join(evidence.title for evidence in item.evidence)
            rows.append([ChartFactory.compact_period_label(item.period), item.level, titles])
        if rows:
            table = detail_ax.table(
                cellText=rows, colLabels=["触发周期", "等级", "命中规则"],
                colWidths=[0.25, 0.12, 0.63], loc="center", cellLoc="left",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 1.35)
            detail_ax.set_title("逐周期规则结果（最近8次触发）", loc="left", fontsize=11)
        else:
            detail_ax.text(0.5, 0.5, "没有历史触发记录", ha="center", va="center")
        return figure

    @staticmethod
    def _draw_risk_line(ax, periods, values, title, xlabel, ylabel, color="#0967B9"):
        ax.clear()
        indexes = list(range(len(periods)))
        ax.plot(indexes, values, marker="o", linewidth=2, color=color)
        tick_indexes, tick_labels, rotation = ChartFactory._axis_ticks(periods)
        ax.set_xticks(tick_indexes, tick_labels, rotation=rotation,
                      ha="right" if rotation else "center")
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        for index, value in enumerate(values):
            ax.text(index, value, str(value), ha="center", va="bottom", fontsize=8)

    @staticmethod
    def unit_risk_detail(periods, values, category_name="",
                         category_values=(), title="", xlabel="", ylabel="",
                         empty_category_message="当前预警暂未归因到具体二级隐患类别"):
        """单位风险总体趋势与可切换二级分类趋势。"""
        figure = Figure(figsize=(11.8, 7.2), dpi=100, constrained_layout=True)
        grid = figure.add_gridspec(2, 1, height_ratios=(1, 1))
        overall_ax = figure.add_subplot(grid[0, 0])
        ChartFactory._draw_risk_line(
            overall_ax, periods, values, title, xlabel, ylabel, "#0967B9"
        )
        category_ax = figure.add_subplot(grid[1, 0])
        ChartFactory._draw_unit_category_axis(
            category_ax, periods, category_values, category_name, xlabel, ylabel,
            empty_category_message,
        )
        return figure

    @staticmethod
    def _draw_unit_category_axis(
        ax, periods, values, category_name, xlabel, ylabel,
        empty_message="当前预警暂未归因到具体二级隐患类别",
    ):
        if not category_name:
            ax.clear()
            ax.axis("off")
            ax.text(
                0.5, 0.5, empty_message,
                ha="center", va="center", color="#6B7A90", fontsize=11,
                transform=ax.transAxes,
            )
            return
        ax.set_axis_on()
        ChartFactory._draw_risk_line(
            ax, periods, values, f"二级隐患趋势：{category_name}",
            xlabel, ylabel, "#E88621",
        )

    @staticmethod
    def update_unit_risk_category(figure, periods, values, category_name,
                                  xlabel="", ylabel=""):
        """只更新单位详情图中的二级分类坐标轴。"""
        if len(figure.axes) < 2:
            raise ValueError("单位风险详情图缺少二级分类坐标轴")
        ChartFactory._draw_unit_category_axis(
            figure.axes[1], periods, values, category_name, xlabel, ylabel
        )
        return figure.axes[1]


# 临时兼容旧导入；该别名只创建Figure，不再调用plt.show()。
Chart = ChartFactory
