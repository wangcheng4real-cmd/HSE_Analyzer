import pandas as pd

from app.core.brake.brake_period import period_axis, period_starts


class BrakeOverallService:

    BRAKE_TYPES = [
        "通报批评",
        "整改通知",
        "挂牌督办",
        "管理约谈",
        "停工令"
    ]

    def type_counts(self, df):
        """五类预警刹车数量，固定返回五类，无数据时补0。"""
        counts = df["预警刹车类型"].value_counts().to_dict()
        return {
            brake_type: int(counts.get(brake_type, 0))
            for brake_type in self.BRAKE_TYPES
        }

    def unit_top10(self, df):
        """按责任单位统计预警刹车数量Top10。"""
        if "责任单位" not in df.columns:
            return {}

        data = df[df["责任单位"].notna()].copy()
        data["责任单位"] = data["责任单位"].astype(str).str.strip()
        data = data[data["责任单位"].ne("")].copy()

        return {
            str(unit): int(count)
            for unit, count in data["责任单位"].value_counts().head(10).items()
        }

    def category_counts(self, df):
        """按问题类别统计；一条记录包含多个类别时拆分计数。"""
        if "问题类别" not in df.columns:
            return {}

        data = df[df["问题类别"].notna()].copy()
        categories = (
            data["问题类别"]
            .astype(str)
            .str.split(r"[,，;；、]", regex=True)
            .explode()
            .astype(str)
            .str.strip()
        )
        categories = categories[categories.ne("")]

        return {
            str(category): int(count)
            for category, count in categories.value_counts().items()
        }

    def category_top10(self, df):
        """返回问题类别Top10，数量降序，同数量按名称排序。"""
        counts = self.category_counts(df)
        return dict(
            sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0])
            )[:10]
        )

    def overall_weekly_trend(self, df, period_type="week"):
        """不区分预警类型，按周、月或季度统计发出时间趋势。"""
        if "发出日期" not in df.columns:
            return {
                "periods": [],
                "values": [],
                "invalid_date_count": len(df)
            }

        data = df.copy()
        data["发出日期"] = pd.to_datetime(
            data["发出日期"],
            errors="coerce"
        )

        invalid_date_count = int(data["发出日期"].isna().sum())
        data = data[data["发出日期"].notna()].copy()

        if data.empty:
            return {
                "periods": [],
                "values": [],
                "invalid_date_count": invalid_date_count
            }

        data["周期开始日期"] = period_starts(data["发出日期"], period_type)
        starts, periods = period_axis(data["周期开始日期"], period_type)
        counts = data.groupby("周期开始日期").size().to_dict()

        return {
            "periods": periods,
            "values": [int(counts.get(start, 0)) for start in starts],
            "invalid_date_count": invalid_date_count
        }
