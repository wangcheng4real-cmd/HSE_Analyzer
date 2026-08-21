from app.core.hazard.results import TrendPoint, TrendSeries


class SpecialTrendService:
    """Overall trend for one real second-level hazard category."""

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def run(self, df_list, category_name):
        points = []
        for source in df_list:
            df = self.preprocessor.normalize_columns(source)
            period = source.attrs.get("时间周期")
            period_start = source.attrs.get("周期开始日期")
            if period is None and not source.empty and "时间周期" in source.columns:
                period = source["时间周期"].iloc[0]
                period_start = source["周期开始日期"].iloc[0]
            if period is None:
                continue

            required = [self.cfg.col_flow, self.cfg.col_category]
            if self.preprocessor.require_columns(df, required):
                count = 0
            else:
                df = self.preprocessor.filter_contractor_flow(df)
                df = self.preprocessor.with_second_category(df)
                count = int(
                    df[self.preprocessor.SECOND_CATEGORY_COL]
                    .eq(category_name).sum()
                )
            points.append(TrendPoint(period, period_start, count))

        points.sort(key=lambda point: point.period_start)
        return TrendSeries(points)
