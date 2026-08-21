from app.core.hazard.results import MultiSeriesTrend


class SpecialAreaTrendService:

    SECOND_CATEGORY_COL = "专项隐患第二级分类"
    MAIN_AREA_COL = "区域大类"

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def _prepare_area_df(self, df):
        """
        数据已由 HazardAnalyzer 执行 common 统一筛选。

        本方法继续：
        1. 筛选“工程公司录入承包商”
        2. 清理区域
        3. 提取区域第一大类
        """
        df = self.preprocessor.normalize_columns(df)
        if self.preprocessor.require_columns(df, [self.cfg.col_flow, self.cfg.col_area]):
            return df.iloc[0:0].copy()
        df = self.preprocessor.filter_contractor_flow(df)
        return self.preprocessor.with_main_area(df)

    def _prepare_special_area_df(self, df):
        """在区域大类数据上提取隐患第二级分类。"""
        df = self._prepare_area_df(df)

        if df.empty or self.cfg.col_category not in df.columns:
            return df.iloc[0:0].copy()

        df = self.preprocessor.with_second_category(df)
        df[self.SECOND_CATEGORY_COL] = df[self.preprocessor.SECOND_CATEGORY_COL]
        return df

    def get_category_totals(self, df_list):
        """
        统计真实的隐患二级分类总数。

        此处不删除区域为空的数据，
        也不根据区域进行筛选。

        数据已经由HazardAnalyzer执行common筛选。
        """

        totals = {}

        for df in df_list:

            df = self.preprocessor.normalize_columns(df)

            required_columns = [
                self.cfg.col_flow,
                self.cfg.col_category
            ]

            if self.preprocessor.require_columns(df, required_columns):
                continue
            df = self.preprocessor.filter_contractor_flow(df)
            df = self.preprocessor.with_second_category(df)
            df[self.SECOND_CATEGORY_COL] = df[self.preprocessor.SECOND_CATEGORY_COL]

            current_counts = (
                df[self.SECOND_CATEGORY_COL]
                .value_counts()
                .to_dict()
            )

            for category_name, count in current_counts.items():

                totals[category_name] = (
                    totals.get(category_name, 0)
                    + int(count)
                )

        return dict(
            sorted(
                totals.items(),
                key=lambda item: (
                    -item[1],
                    item[0]
                )
            )
        )
    def run(self, df_list, category_name):
        """
        按“隐患二级分类 + 区域第一大类 + 时间周期”统计。

        返回：
        {
            "periods": [...],
            "series": {"区域大类": [...]},
            "totals": {"区域大类": 累计数量}
        }
        """
        periods = []
        period_area_counts = []
        all_areas = set()

        for df in df_list:
            df = df.copy()

            period = df.attrs.get("时间周期")
            if period is None and not df.empty and "时间周期" in df.columns:
                period = df["时间周期"].iloc[0]
            if period is None:
                continue

            area_df = self._prepare_area_df(df)

            if not area_df.empty:
                all_areas.update(
                    area_df[self.MAIN_AREA_COL].unique()
                )

            special_df = self._prepare_special_area_df(df)

            if special_df.empty:
                periods.append(period)
                period_area_counts.append({})
                continue

            special_df = special_df[
                special_df[self.SECOND_CATEGORY_COL].eq(category_name)
            ].copy()

            area_counts = (
                special_df[self.MAIN_AREA_COL]
                .value_counts()
                .to_dict()
            )

            periods.append(period)
            period_area_counts.append(area_counts)

        if not periods:
            return MultiSeriesTrend()

        series = {}
        totals = {}

        for area in sorted(all_areas):
            values = [
                int(area_counts.get(area, 0))
                for area_counts in period_area_counts
            ]

            series[area] = values
            totals[area] = sum(values)

        return MultiSeriesTrend(periods, series, totals)
