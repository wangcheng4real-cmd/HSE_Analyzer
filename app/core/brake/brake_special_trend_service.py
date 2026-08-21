import pandas as pd

from app.core.brake.brake_period import period_axis, period_starts


class BrakeSpecialTrendService:
    """Problem-category trends by responsible unit across all brake types."""

    CATEGORY_SPLIT_PATTERN = r"[,，;；、]"

    def _with_categories(self, df):
        if df is None or df.empty or "问题类别" not in df.columns:
            return pd.DataFrame()
        data = df[df["问题类别"].notna()].copy()
        data["专项问题类别"] = (
            data["问题类别"].astype(str)
            .str.split(self.CATEGORY_SPLIT_PATTERN, regex=True)
        )
        data = data.explode("专项问题类别")
        data["专项问题类别"] = data["专项问题类别"].astype(str).str.strip()
        return data[data["专项问题类别"].ne("")].copy()

    def category_totals(self, df):
        data = self._with_categories(df)
        if data.empty:
            return {}
        counts = data["专项问题类别"].value_counts().to_dict()
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def category_period_trend(self, df, category, period_type="week"):
        """Trend for one problem category across all brake records."""
        empty = {"periods": [], "values": [], "invalid_date_count": 0}
        if df is None or df.empty or "发出日期" not in df.columns:
            return empty

        all_data = df.copy()
        all_data["发出日期"] = pd.to_datetime(all_data["发出日期"], errors="coerce")
        dated_all = all_data[all_data["发出日期"].notna()].copy()
        if dated_all.empty:
            result = dict(empty)
            result["invalid_date_count"] = len(all_data)
            return result

        dated_all["周期开始日期"] = period_starts(
            dated_all["发出日期"], period_type
        )
        periods, labels = period_axis(
            dated_all["周期开始日期"], period_type
        )

        category_data = self._with_categories(all_data)
        category_data = category_data[
            category_data["专项问题类别"].eq(str(category).strip())
        ].copy()
        invalid_count = int(category_data["发出日期"].isna().sum())
        valid = category_data[category_data["发出日期"].notna()].copy()
        if not valid.empty:
            valid["周期开始日期"] = period_starts(
                valid["发出日期"], period_type
            )
            counts = valid.groupby("周期开始日期").size().to_dict()
        else:
            counts = {}

        return {
            "periods": labels,
            "values": [int(counts.get(period, 0)) for period in periods],
            "invalid_date_count": invalid_count,
        }

    def category_unit_weekly_trend(self, df, category, period_type="week"):
        empty = {
            "periods": [], "series": {}, "totals": {},
            "invalid_date_count": 0,
        }
        if df is None or df.empty or "发出日期" not in df.columns:
            return empty

        all_data = df.copy()
        all_data["发出日期"] = pd.to_datetime(all_data["发出日期"], errors="coerce")
        dated_all = all_data[all_data["发出日期"].notna()].copy()
        if dated_all.empty:
            result = dict(empty)
            result["invalid_date_count"] = len(all_data)
            return result

        dated_all["周期开始日期"] = period_starts(
            dated_all["发出日期"], period_type
        )
        periods, labels = period_axis(
            dated_all["周期开始日期"], period_type
        )

        category_data = self._with_categories(all_data)
        category_data = category_data[
            category_data["专项问题类别"].eq(str(category).strip())
        ].copy()
        if "责任单位" not in category_data.columns:
            category_data = category_data.iloc[0:0].copy()
        else:
            category_data = category_data[category_data["责任单位"].notna()].copy()
            category_data["责任单位"] = category_data["责任单位"].astype(str).str.strip()
            category_data = category_data[category_data["责任单位"].ne("")].copy()

        invalid_count = int(category_data["发出日期"].isna().sum()) if not category_data.empty else 0
        valid = category_data[category_data["发出日期"].notna()].copy()
        if not valid.empty:
            valid["周期开始日期"] = period_starts(
                valid["发出日期"], period_type
            )

        totals = category_data["责任单位"].value_counts().to_dict() if not category_data.empty else {}
        totals = dict(sorted(totals.items(), key=lambda item: (-item[1], item[0])))
        series = {}
        for unit in totals:
            counts = (
                valid[valid["责任单位"].eq(unit)]
                .groupby("周期开始日期").size().to_dict()
            ) if not valid.empty else {}
            series[unit] = [int(counts.get(period, 0)) for period in periods]
        return {
            "periods": labels,
            "series": series,
            "totals": totals,
            "invalid_date_count": invalid_count,
        }
