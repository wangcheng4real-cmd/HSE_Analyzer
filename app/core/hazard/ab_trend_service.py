from app.core.hazard.results import TrendPoint, TrendSeries


class ABTrendService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def run(self, df_list):

        result = []

        for df in df_list:

            df = df.copy()

            # 先取时间周期
            period = df.attrs.get("时间周期")
            period_start = df.attrs.get("周期开始日期")
            if period is None and not df.empty:
                period = df["时间周期"].iloc[0]
                period_start = df["周期开始日期"].iloc[0]
            if period is None:
                continue

            # 和 LevelService 保持完全一致的流程过滤方式
            df = self.preprocessor.filter_contractor_flow(df)
            df = self.preprocessor.clean_text_column(df, self.cfg.col_level)

            # 和 LevelService 保持完全一致的等级统计方式
            level_count = df[self.cfg.col_level].value_counts()

            a_count = level_count.get("A", 0)
            b_count = level_count.get("B", 0)

            count = a_count + b_count


            result.append(TrendPoint(period, period_start, int(count)))

        result.sort(
            key=lambda point: point.period_start
        )
        return TrendSeries(result)
