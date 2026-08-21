from app.core.hazard.hazard_filter import HazardFilter
from app.core.hazard.hazard_preprocessor import HazardPreprocessor


from app.core.hazard.level_service import LevelService
from app.core.hazard.unit_service import UnitService
from app.core.hazard.category_service import CategoryService
from app.core.hazard.trend_service import TrendService
from app.core.hazard.area_service import AreaService
from app.core.hazard.interface_service import InterfaceService


from app.core.hazard.unit_profile_service import UnitProfileService
from app.core.hazard.ab_level_service import ABLevelService

from app.core.hazard.unit_ab_service import UnitABService
from app.core.hazard.unit_team_service import UnitTeamService
from app.core.hazard.unit_verify_service import UnitVerifyService
from app.core.hazard.unit_trend_service import UnitTrendService

from app.core.hazard.ab_trend_service import ABTrendService


from app.core.hazard.area_profile_service import AreaProfileService
from app.core.hazard.area_ab_service import AreaABService
from app.core.hazard.area_trend_service import AreaTrendService
from app.core.hazard.special_unit_trend_service import ( SpecialUnitTrendService)
from app.core.hazard.special_area_trend_service import ( SpecialAreaTrendService)
from app.core.hazard.special_trend_service import SpecialTrendService

class HazardAnalyzer:


    def __init__(self, cfg):

        self.cfg = cfg
        self.preprocessor = HazardPreprocessor(cfg)


        self.filter_engine = HazardFilter(cfg)


        # 总体分析

        self.level_service = LevelService(cfg, self.preprocessor)

        self.unit_service = UnitService(cfg, self.preprocessor)

        self.category_service = CategoryService(cfg, self.preprocessor)

        self.area_service = AreaService(cfg, self.preprocessor)

        self.interface_service = InterfaceService(cfg, self.preprocessor)

        self.ab_level_service = ABLevelService(cfg, self.preprocessor)



        # 趋势分析

        self.trend_service = TrendService(cfg, self.preprocessor)

        self.ab_trend_service = ABTrendService(cfg, self.preprocessor)



        # 单位画像

        self.unit_profile_service = UnitProfileService(cfg, self.preprocessor)

        self.unit_ab_service = UnitABService(cfg, self.preprocessor)

        self.unit_team_service = UnitTeamService(cfg, self.preprocessor)

        self.unit_verify_service = UnitVerifyService(cfg, self.preprocessor)

        self.unit_trend_service = UnitTrendService(cfg, self.preprocessor)



        # 区域画像

        self.area_profile_service = AreaProfileService(cfg, self.preprocessor)

        self.area_ab_service = AreaABService(cfg, self.preprocessor)

        self.area_trend_service = AreaTrendService(cfg, self.preprocessor)

        # 专项隐患（单位）分析
        self.special_unit_trend_service = SpecialUnitTrendService(cfg, self.preprocessor)
        # 专项隐患（区域）分析
        self.special_area_trend_service = SpecialAreaTrendService(cfg, self.preprocessor)
        self.special_trend_service = SpecialTrendService(cfg, self.preprocessor)

    # =========================
    # 数据预处理
    # =========================

    def prepare(self, df):

        return self.filter_engine.apply(df)



    def prepare_df_list(self, df_list):

        new_list = []


        for df in df_list:

            df = df.copy()

            period = df["时间周期"].iloc[0]
            period_start = df["周期开始日期"].iloc[0]

            df = self.prepare(df)

            df["时间周期"] = period
            df["周期开始日期"] = period_start
            df.attrs["时间周期"] = period
            df.attrs["周期开始日期"] = period_start

            new_list.append(df)

        return sorted(
            new_list,
            key=lambda item: item.attrs["周期开始日期"]
        )



    # =========================
    # 总体分析
    # =========================

    def level_analysis(self, df):

        df = self.prepare(df)

        return self.level_service.run(df)



    def unit_analysis(self, df):

        df = self.prepare(df)

        return self.unit_service.run(df)



    def category_main_analysis(self, df):

        df = self.prepare(df)

        return self.category_service.run_main_category(df)



    def category_sub_analysis(self, df):

        df = self.prepare(df)

        return self.category_service.run_sub_category(
            df,
            top_n=10
        )



    def area_analysis(self, df):

        df = self.prepare(df)

        return self.area_service.run(df)



    def interface_analysis(self, df):

        df = self.prepare(df)

        return self.interface_service.run(df)



    def ab_level_analysis(self, df):

        df = self.prepare(df)

        return self.ab_level_service.run(df)



    # =========================
    # 趋势分析
    # =========================

    def trend_analysis(self, df_list):
        return self.period_trend(df_list).to_legacy()

    def period_trend(self, df_list):
        return self.trend_service.period_trend(self.prepare_df_list(df_list))



    def ab_trend_analysis(self, df_list):
        return self.ab_period_trend(df_list).to_legacy()

    def ab_period_trend(self, df_list):
        return self.ab_trend_service.run(self.prepare_df_list(df_list))



    # =========================
    # 单位画像
    # =========================

    def unit_profile_units(self, df):

        df = self.prepare(df)

        return self.unit_profile_service.get_units(df)



    def unit_profile_top5(self, df, unit):

        df = self.prepare(df)

        return self.unit_profile_service.unit_category_top5(
            df,
            unit
        )



    def unit_ab_units(self, df):

        df = self.prepare(df)

        return self.unit_ab_service.get_units(df)



    def unit_ab_top3(self, df, unit):

        df = self.prepare(df)

        return self.unit_ab_service.unit_ab_top3(
            df,
            unit
        )



    def unit_team_units(self, df):

        df = self.prepare(df)

        return self.unit_team_service.get_units(df)



    def unit_team_top5(self, df, unit):

        df = self.prepare(df)

        return self.unit_team_service.unit_team_top5(
            df,
            unit
        )



    def unit_verify_analysis(self, df):

        df = self.prepare(df)

        return self.unit_verify_service.run(df)



    # =========================
    # 单位趋势
    # =========================

    def unit_trend_units(self, df):

        df = self.prepare(df)

        return self.unit_trend_service.get_units(df)



    def unit_trend_analysis(self, df_list, unit):
        return self.unit_period_trend(df_list, unit).to_legacy()

    def unit_period_trend(self, df_list, unit):
        return self.unit_trend_service.unit_trend(
            self.prepare_df_list(df_list), unit
        )



    # =========================
    # 区域画像
    # =========================

    def area_profile_areas(self, df):

        df = self.prepare(df)

        return self.area_profile_service.get_areas(df)



    def area_profile_top5(self, df, area):

        df = self.prepare(df)

        return self.area_profile_service.area_category_top5(
            df,
            area
        )



    def area_ab_areas(self, df):

        df = self.prepare(df)

        return self.area_ab_service.get_areas(df)



    def area_ab_top3(self, df, area):

        df = self.prepare(df)

        return self.area_ab_service.area_ab_top3(
            df,
            area
        )



    # =========================
    # 区域趋势
    # =========================

    def area_trend_areas(self, df):

        df = self.prepare(df)

        return self.area_trend_service.get_areas(df)



    def area_trend_analysis(self, df_list, area):
        return self.area_period_trend(df_list, area).to_legacy()

    def area_period_trend(self, df_list, area):
        return self.area_trend_service.area_trend(
            self.prepare_df_list(df_list), area
        )
    # =========================
    # 专项隐患（单位）分析
    # =========================
    def special_unit_category_totals(self, df_list):
        """
        专项隐患二级分类总数。

        必须先经过 common 统一筛选。
        """
        df_list = self.prepare_df_list(df_list)

        return (
            self.special_unit_trend_service
            .get_category_totals(df_list)
        )

    def special_category_period_trend(self, df_list, category_name):
        return self.special_trend_service.run(
            self.prepare_df_list(df_list), category_name
        )
    def special_unit_trend_analysis(
        self,
        df_list,
        category_name
    ):

        return self.special_unit_period_trend(df_list, category_name).to_legacy()

    def special_unit_period_trend(self, df_list, category_name):
        return self.special_unit_trend_service.run(
            self.prepare_df_list(df_list), category_name
        )
    # =========================
    # 专项隐患（区域）分析
    # =========================

    def special_area_category_totals(self, df_list):
        """
        专项隐患区域分析的二级分类数量。
        """
        df_list = self.prepare_df_list(df_list)

        return (
            self.special_area_trend_service
            .get_category_totals(df_list)
        )


    def special_area_trend_analysis(
        self,
        df_list,
        category_name
    ):
        """
        指定二级分类下，各区域第一大类的趋势。
        """
        return self.special_area_period_trend(df_list, category_name).to_legacy()

    def special_area_period_trend(self, df_list, category_name):
        return self.special_area_trend_service.run(
            self.prepare_df_list(df_list), category_name
        )
