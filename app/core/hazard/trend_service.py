from app.core.hazard.results import TrendPoint, TrendSeries


class TrendService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def period_trend(self, df_list):

        result = []

        for df in df_list:

            df = df.copy()

            df = self.preprocessor.normalize_columns(df)

            period = df.attrs.get("时间周期")
            period_start = df.attrs.get("周期开始日期")
            if period is None and not df.empty:
                period = df["时间周期"].iloc[0]
                period_start = df["周期开始日期"].iloc[0]
            if period is None:
                continue

            # 只分析工程公司录入承包商
            df = self.preprocessor.filter_contractor_flow(df)

            result.append(TrendPoint(period, period_start, len(df)))

        result.sort(
            key=lambda point: point.period_start
        )
        return TrendSeries(result)

    def monthly_trend(self, df_list):
        """兼容旧接口；周期已不再限定为月。"""
        return self.period_trend(df_list).to_legacy()
