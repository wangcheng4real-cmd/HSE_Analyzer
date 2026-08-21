import pandas as pd

from app.core.brake.brake_period import period_axis, period_starts


class BrakeUnitProfileService:
    """预警刹车单位画像统计服务。"""

    def _prepare_units(self, df):
        if df is None or df.empty or "责任单位" not in df.columns:
            return df.iloc[0:0].copy() if df is not None else None

        data = df[df["责任单位"].notna()].copy()
        data["责任单位"] = data["责任单位"].astype(str).str.strip()
        return data[data["责任单位"].ne("")].copy()

    def unit_counts(self, df):
        """返回各单位预警刹车数量，按数量降序。"""
        data = self._prepare_units(df)
        if data is None or data.empty:
            return {}

        counts = data["责任单位"].value_counts().to_dict()
        return dict(
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        )

    def unit_type_top3(self, df, unit):
        """指定单位的预警刹车类别Top3。"""
        data = self._prepare_units(df)
        if data is None or data.empty or "预警刹车类型" not in data.columns:
            return {}

        data = data[data["责任单位"].eq(str(unit).strip())].copy()
        counts = data["预警刹车类型"].value_counts().to_dict()
        return dict(
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        )

    def unit_problem_category_top3(self, df, unit):
        """指定单位的问题类别Top3，多类别字段拆分后统计。"""
        data = self._prepare_units(df)
        if data is None or data.empty or "问题类别" not in data.columns:
            return {}

        data = data[data["责任单位"].eq(str(unit).strip())].copy()
        data = data[data["问题类别"].notna()].copy()

        categories = (
            data["问题类别"]
            .astype(str)
            .str.split(r"[,，;；、]", regex=True)
            .explode()
            .astype(str)
            .str.strip()
        )
        categories = categories[categories.ne("")]
        counts = categories.value_counts().to_dict()

        return dict(
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        )

    def unit_weekly_trend(self, df, unit, period_type="week"):
        """
        指定单位的周趋势。周期为周一至周日，
        时间范围按全部有效预警数据确定，单位无数据周补0。
        """
        if df is None or df.empty or "发出日期" not in df.columns:
            return {"periods": [], "values": [], "invalid_date_count": 0}

        all_data = df.copy()
        all_data["发出日期"] = pd.to_datetime(
            all_data["发出日期"], errors="coerce"
        )
        dated_all = all_data[all_data["发出日期"].notna()].copy()
        if dated_all.empty:
            return {
                "periods": [],
                "values": [],
                "invalid_date_count": len(all_data)
            }

        dated_all["周期开始日期"] = period_starts(
            dated_all["发出日期"], period_type
        )
        all_periods, labels = period_axis(
            dated_all["周期开始日期"], period_type
        )

        unit_data = self._prepare_units(all_data)
        unit_data = unit_data[unit_data["责任单位"].eq(str(unit).strip())].copy()
        invalid_date_count = int(unit_data["发出日期"].isna().sum())
        unit_data = unit_data[unit_data["发出日期"].notna()].copy()

        if not unit_data.empty:
            unit_data["周期开始日期"] = period_starts(
                unit_data["发出日期"], period_type
            )
            counts = unit_data.groupby("周期开始日期").size().to_dict()
        else:
            counts = {}

        values = [int(counts.get(period, 0)) for period in all_periods]

        return {
            "periods": labels,
            "values": values,
            "invalid_date_count": invalid_date_count
        }
