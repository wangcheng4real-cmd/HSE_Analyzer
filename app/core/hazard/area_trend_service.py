from app.core.hazard.results import TrendPoint, TrendSeries


class AreaTrendService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def get_areas(self, df):
        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.with_main_area(df)

        counts = (
            df["区域大类"]
            .value_counts()
            .to_dict()
        )

        return dict(
            sorted(
                counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0]
                )
            )
        )

    def area_trend(self, df_list, area):

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
            df = self.preprocessor.with_main_area(df)

            data = df[
                df["区域大类"] == area
            ]

            result.append(TrendPoint(period, period_start, len(data)))

        result.sort(
            key=lambda point: point.period_start
        )
        return TrendSeries(result)
