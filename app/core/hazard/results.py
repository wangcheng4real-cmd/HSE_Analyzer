from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrendPoint:
    period: str
    period_start: object
    count: int

    def to_legacy(self):
        return {
            "时间周期": self.period,
            "周期开始日期": self.period_start,
            "数量": self.count,
        }


@dataclass
class TrendSeries:
    points: list = field(default_factory=list)

    @property
    def periods(self):
        return [point.period for point in self.points]

    @property
    def counts(self):
        return [point.count for point in self.points]

    @property
    def empty(self):
        return not self.points

    def to_legacy(self):
        return [point.to_legacy() for point in self.points]


@dataclass
class MultiSeriesTrend:
    periods: list = field(default_factory=list)
    series: dict = field(default_factory=dict)
    totals: dict = field(default_factory=dict)

    @property
    def empty(self):
        return not self.periods

    def to_legacy(self):
        return {
            "periods": list(self.periods),
            "series": dict(self.series),
            "totals": dict(self.totals),
        }
