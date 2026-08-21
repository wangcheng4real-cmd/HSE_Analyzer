from app.core.brake.brake_filter import BrakeFilter
from app.core.brake.brake_overall_service import BrakeOverallService
from app.core.brake.brake_unit_profile_service import BrakeUnitProfileService
from app.core.brake.brake_special_trend_service import BrakeSpecialTrendService


class BrakeAnalyzer:
    """预警刹车分析器入口。

    第一阶段只负责接入加载后的数据；
    后续的分类、单位、区域和趋势服务统一从这里接入。
    """

    def __init__(self):
        self.filter = BrakeFilter()
        self.overall_service = BrakeOverallService()
        self.unit_profile_service = BrakeUnitProfileService()
        self.special_trend_service = BrakeSpecialTrendService()

    def prepare(self, df, brake_types=None):
        return self.filter.apply(df, brake_types=brake_types)

    def type_counts(self, df):
        return self.overall_service.type_counts(self.prepare(df))

    def unit_top10(self, df):
        return self.overall_service.unit_top10(self.prepare(df))

    def category_counts(self, df):
        return self.overall_service.category_counts(self.prepare(df))

    def category_top10(self, df):
        return self.overall_service.category_top10(self.prepare(df))

    def overall_weekly_trend(self, df, period_type="week"):
        return self.overall_service.overall_weekly_trend(
            self.prepare(df), period_type
        )

    def unit_counts(self, df):
        return self.unit_profile_service.unit_counts(self.prepare(df))

    def unit_type_top3(self, df, unit):
        return self.unit_profile_service.unit_type_top3(self.prepare(df), unit)

    def unit_problem_category_top3(self, df, unit):
        return self.unit_profile_service.unit_problem_category_top3(
            self.prepare(df), unit
        )

    def unit_weekly_trend(self, df, unit, period_type="week"):
        return self.unit_profile_service.unit_weekly_trend(
            self.prepare(df), unit, period_type
        )

    def special_category_totals(self, df):
        return self.special_trend_service.category_totals(self.prepare(df))

    def special_category_period_trend(self, df, category, period_type="week"):
        return self.special_trend_service.category_period_trend(
            self.prepare(df), category, period_type
        )

    def special_category_unit_weekly_trend(self, df, category, period_type="week"):
        return self.special_trend_service.category_unit_weekly_trend(
            self.prepare(df), category, period_type
        )
