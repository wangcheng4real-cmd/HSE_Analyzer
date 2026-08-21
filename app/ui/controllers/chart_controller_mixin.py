from app.charts.chart import ChartFactory
from app.ui.components.chart_window import ChartWindow


class ChartControllerMixin:
    def show_bar(self, x, y, title="", xlabel="", ylabel=""):
        figure = ChartFactory.bar(x, y, title, xlabel, ylabel)
        return ChartWindow.show(self.app.root, figure, title)

    def show_pie(self, labels, values, title=""):
        figure = ChartFactory.pie(labels, values, title)
        return ChartWindow.show(self.app.root, figure, title)

    def show_line(self, x, y, title="", xlabel="", ylabel=""):
        figure = ChartFactory.line(x, y, title, xlabel, ylabel)
        return ChartWindow.show(self.app.root, figure, title)
