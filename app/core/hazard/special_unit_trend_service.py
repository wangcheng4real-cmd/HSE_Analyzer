from app.core.hazard.results import MultiSeriesTrend


class SpecialUnitTrendService:

    SECOND_CATEGORY_COL = "专项隐患第二级分类"

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def _prepare_special_df(self, df):
        """
        此处接收到的数据已经经过 common 筛选。

        本方法继续完成：
        1. 筛选“工程公司录入承包商”
        2. 清理责任单位
        3. 提取隐患二级分类
        """
        df = self.preprocessor.normalize_columns(df)
        required = [self.cfg.col_flow, self.cfg.col_unit, self.cfg.col_category]
        if self.preprocessor.require_columns(df, required):
            return df.iloc[0:0].copy()
        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_unit)
        df = self.preprocessor.with_second_category(df)
        df[self.SECOND_CATEGORY_COL] = df[self.preprocessor.SECOND_CATEGORY_COL]
        return df

    def get_category_totals(self, df_list):
        """
        统计真实的隐患二级分类总数。

        此处不删除责任单位为空的数据，
        也不根据责任单位进行筛选。

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
        专项隐患（单位）趋势分析。

        筛选顺序：
        1. common统一筛选由HazardAnalyzer提前完成
        2. 筛选流程类型：工程公司录入承包商
        3. 提取隐患分类第二级
        4. 筛选第二级分类等于category_name
        5. 按单位和时间周期统计

        所有有效责任单位都会保留；
        某周期没有该类隐患时，数量补0。
        """

        periods = []
        period_unit_counts = []
        all_units = set()

        for df in df_list:

            df = self.preprocessor.normalize_columns(df)

            period = df.attrs.get("时间周期")
            if period is None and not df.empty and "时间周期" in df.columns:
                period = df["时间周期"].iloc[0]
            if period is None:
                continue

            # =====================================
            # 先获取当前周期全部有效责任单位
            # 此时数据已经经过common筛选
            # =====================================

            required_columns = [
                self.cfg.col_flow,
                self.cfg.col_unit,
                self.cfg.col_category
            ]

            if self.preprocessor.require_columns(df, required_columns):
                periods.append(period)
                period_unit_counts.append({})
                continue

            flow_df = self.preprocessor.filter_contractor_flow(df)
            unit_df = self.preprocessor.clean_text_column(flow_df, self.cfg.col_unit)

            all_units.update(
                unit_df[self.cfg.col_unit].unique()
            )

            # =====================================
            # 提取二级分类
            # =====================================

            category_df = self._prepare_special_df(df)

            if category_df.empty:
                periods.append(period)
                period_unit_counts.append({})
                continue

            # =====================================
            # 筛选选中的二级分类
            # =====================================

            special_df = category_df[
                category_df[self.SECOND_CATEGORY_COL]
                .eq(category_name)
            ].copy()

            # =====================================
            # 统计当前周期各单位数量
            # =====================================

            unit_counts = (
                special_df[self.cfg.col_unit]
                .value_counts()
                .to_dict()
            )

            periods.append(period)
            period_unit_counts.append(unit_counts)

        # 没有有效周期
        if not periods:
            return MultiSeriesTrend()

        # =====================================
        # 为每个单位生成完整趋势
        # 没有发生该类型隐患的周期补0
        # =====================================

        series = {}
        totals = {}

        for unit in sorted(all_units):

            values = [
                int(unit_counts.get(unit, 0))
                for unit_counts in period_unit_counts
            ]

            series[unit] = values
            totals[unit] = sum(values)

        return MultiSeriesTrend(periods, series, totals)
