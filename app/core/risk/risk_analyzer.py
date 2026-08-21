from collections import defaultdict

import pandas as pd

from app.core.brake.brake_filter import BrakeFilter
from app.core.brake.brake_overall_service import BrakeOverallService
from app.core.brake.brake_period import complete_periods, period_label, period_starts
from app.core.hazard.hazard_filter import HazardFilter
from app.core.hazard.hazard_preprocessor import HazardPreprocessor
from app.core.risk.results import (
    AlertResult, AlertSection, DashboardResult, DateBounds, MultiSeriesResult,
    PeriodRisk, RiskEvidence, RiskObject, TrendResult,
)
from app.core.risk.rule_repository import RiskRuleRepository


class RiskAnalyzer:
    BRAKE_TYPES = list(BrakeOverallService.BRAKE_TYPES)
    LEVEL_ORDER = {"红色": 0, "橙色": 1, "黄色": 2}

    def __init__(self, cfg, rule_repository=None):
        self.cfg = cfg
        self.preprocessor = HazardPreprocessor(cfg)
        self.hazard_filter = HazardFilter(cfg)
        self.brake_filter = BrakeFilter()
        self.rule_repository = rule_repository or RiskRuleRepository()

    @staticmethod
    def _valid_dates(df, column):
        if df is None or df.empty or column not in df.columns:
            return pd.Series(dtype="datetime64[ns]")
        return pd.to_datetime(df[column], errors="coerce").dropna().dt.normalize()

    def date_bounds(self, hazard_df=None, brake_df=None):
        dates = [
            self._valid_dates(hazard_df, self.cfg.col_date),
            self._valid_dates(brake_df, "发出日期"),
        ]
        dates = [item for item in dates if not item.empty]
        if not dates:
            return DateBounds()
        combined = pd.concat(dates, ignore_index=True)
        return DateBounds(combined.min(), combined.max())

    @staticmethod
    def _range(start, end):
        start = pd.Timestamp(start).normalize()
        end = pd.Timestamp(end).normalize()
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
        return start, end

    def validate_range(self, hazard_df, brake_df, start, end):
        start, end = self._range(start, end)
        bounds = self.date_bounds(hazard_df, brake_df)
        if bounds.empty:
            raise ValueError("请先在隐患分析或预警刹车分析中加载数据")
        if start < bounds.start or end > bounds.end:
            raise ValueError("选择日期超出已加载数据的有效日期范围")
        return start, end

    @staticmethod
    def _filter_dates(df, column, start, end):
        if df is None or df.empty or column not in df.columns:
            return pd.DataFrame()
        result = df.copy()
        result[column] = pd.to_datetime(result[column], errors="coerce")
        result = result[result[column].notna()].copy()
        normalized = result[column].dt.normalize()
        return result[(normalized >= start) & (normalized <= end)].copy()

    @staticmethod
    def _axis(start, end, period_type):
        starts = period_starts(pd.Series([start, end]), period_type)
        axis = complete_periods(starts.iloc[0], starts.iloc[1], period_type)
        return list(axis), [period_label(item, period_type) for item in axis]

    @staticmethod
    def _period_end(start, period_type):
        if period_type == "week":
            return start + pd.Timedelta(days=6)
        if period_type == "month":
            return start + pd.offsets.MonthEnd(0)
        return start + pd.offsets.QuarterEnd(startingMonth=12)

    def _complete_axis(self, start, end, period_type):
        axis, labels = self._axis(start, end, period_type)
        kept_axis, kept_labels, excluded = [], [], []
        for point, label in zip(axis, labels):
            if point >= start and self._period_end(point, period_type) <= end:
                kept_axis.append(point)
                kept_labels.append(label)
            else:
                excluded.append(label)
        return kept_axis, kept_labels, excluded

    def _hazard_data(self, df, start, end):
        if df is None or df.empty:
            return pd.DataFrame()
        data = self.hazard_filter.apply(self.preprocessor.normalize_columns(df))
        data = self._filter_dates(data, self.cfg.col_date, start, end)
        return self.preprocessor.filter_contractor_flow(data)

    def _brake_data(self, df, start, end):
        if df is None or df.empty:
            return pd.DataFrame()
        data = self.brake_filter.apply(df)
        return self._filter_dates(data, "发出日期", start, end)

    @staticmethod
    def _clean_dimension(df, column):
        if df.empty or column not in df.columns:
            return df.iloc[0:0].copy()
        result = df[df[column].notna()].copy()
        result[column] = result[column].astype(str).str.strip()
        return result[result[column].ne("")].copy()

    def _multi_series(self, df, date_column, dimension, start, end, period_type):
        axis, labels = self._axis(start, end, period_type)
        return MultiSeriesResult(labels, self._series_for_axis(
            df, date_column, dimension, axis, period_type
        ))

    def _series_for_axis(self, df, date_column, dimension, axis, period_type):
        data = self._clean_dimension(df, dimension)
        if data.empty:
            return {}
        data["周期开始日期"] = period_starts(data[date_column], period_type)
        grouped = data.groupby(["周期开始日期", dimension]).size()
        totals = data[dimension].value_counts().to_dict()
        names = sorted(totals, key=lambda name: (-totals[name], str(name)))
        return {
            str(name): [int(grouped.get((point, name), 0)) for point in axis]
            for name in names
        }

    def _overall_trend(self, df, date_column, start, end, period_type):
        axis, labels = self._axis(start, end, period_type)
        if df.empty or date_column not in df.columns:
            return TrendResult(labels, [0 for _ in axis])
        data = df.copy()
        data["周期开始日期"] = period_starts(data[date_column], period_type)
        counts = data.groupby("周期开始日期").size().to_dict()
        return TrendResult(labels, [int(counts.get(point, 0)) for point in axis])

    def dashboard(self, hazard_df, brake_df, start, end, period_type="week"):
        start, end = self.validate_range(hazard_df, brake_df, start, end)
        hazard = self._hazard_data(hazard_df, start, end)
        brake = self._brake_data(brake_df, start, end)
        levels = {name: 0 for name in ("A", "B", "C", "D")}
        if not hazard.empty and self.cfg.col_level in hazard.columns:
            normalized = hazard[self.cfg.col_level].astype(str).str.strip().str.upper()
            normalized = normalized.str.replace("级", "", regex=False)
            counts = normalized.value_counts().to_dict()
            levels.update({name: int(counts.get(name, 0)) for name in levels})
        brake_types = {name: 0 for name in self.BRAKE_TYPES}
        if not brake.empty and "预警刹车类型" in brake.columns:
            counts = brake["预警刹车类型"].value_counts().to_dict()
            brake_types.update({name: int(counts.get(name, 0)) for name in brake_types})
        return DashboardResult(
            hazard_levels=levels,
            hazard_trend=self._overall_trend(hazard, self.cfg.col_date, start, end, period_type),
            brake_types=brake_types,
            brake_trend=self._overall_trend(brake, "发出日期", start, end, period_type),
            hazard_message="请先在隐患分析中加载数据" if hazard_df is None or hazard_df.empty else "",
            brake_message="请先在预警刹车分析中加载数据" if brake_df is None or brake_df.empty else "",
        )

    @staticmethod
    def _risk_level(evidence):
        severe = sum(item.severe for item in evidence)
        total = len(evidence)
        if severe >= 2 or total >= 3:
            return "红色"
        if severe >= 1 or total >= 2:
            return "橙色"
        return "黄色"

    @staticmethod
    def _baseline_window(dimension_rules, period_type):
        return {
            "week": dimension_rules.baseline_week_window,
            "month": dimension_rules.baseline_month_window,
            "quarter": dimension_rules.baseline_quarter_window,
        }[period_type]

    def _basic_evidence(self, values, ab_values, index, dimension_rules, period_type,
                        category_series=None, category_ab_series=None,
                        include_category_details=False):
        evidence = []
        category_series = category_series or {}
        category_ab_series = category_ab_series or {}
        current = values[index]
        if dimension_rules.baseline_enabled:
            window = self._baseline_window(dimension_rules, period_type)
            if index >= window:
                history = values[index - window:index]
                baseline = sum(history) / window
                rate_limit = dimension_rules.baseline_rate
                absolute_limit = dimension_rules.baseline_absolute
                increase = current - baseline
                rate = None if baseline == 0 else increase / baseline * 100
                if increase >= absolute_limit and (
                    (baseline == 0 and current >= absolute_limit)
                    or (rate is not None and rate >= rate_limit)
                ):
                    related = []
                    for category, sequence in category_series.items():
                        category_history = sequence[index - window:index]
                        category_baseline = sum(category_history) / window
                        if sequence[index] > category_baseline:
                            related.append((sequence[index] - category_baseline, str(category)))
                    related.sort(key=lambda item: (-item[0], item[1]))
                    rate_text = "历史均值为0" if rate is None else f"高出{rate:.1f}%"
                    evidence.append(RiskEvidence(
                        "baseline", "历史基线异常",
                        f"本期{current}条，前{window}期均值{baseline:.1f}条，{rate_text}，增加{increase:.1f}条",
                        related_categories=tuple(category for _delta, category in related),
                    ))
        if (dimension_rules.continuous_enabled
                and index >= dimension_rules.continuous_periods - 1):
            recent = values[index - dimension_rules.continuous_periods + 1:index + 1]
            if all(later > earlier for earlier, later in zip(recent, recent[1:])):
                increase = recent[-1] - recent[0]
                rate = None if recent[0] == 0 else increase / recent[0] * 100
                if increase >= dimension_rules.continuous_absolute and (
                    recent[0] == 0 or rate >= dimension_rules.continuous_rate
                ):
                    related = []
                    start = index - dimension_rules.continuous_periods + 1
                    for category, sequence in category_series.items():
                        category_recent = sequence[start:index + 1]
                        if len(category_recent) == dimension_rules.continuous_periods and all(
                            later > earlier
                            for earlier, later in zip(category_recent, category_recent[1:])
                        ):
                            related.append((category_recent[-1], str(category)))
                    related.sort(key=lambda item: (-item[0], item[1]))
                    rate_text = "起始值为0" if rate is None else f"首末增长{rate:.1f}%"
                    evidence.append(RiskEvidence(
                        "continuous", "连续恶化",
                        f"最近{dimension_rules.continuous_periods}期逐期上升：{recent}，{rate_text}",
                        related_categories=tuple(category for _current, category in related),
                    ))
        if dimension_rules.ab_enabled:
            ab_count = ab_values[index]
            ratio = ab_count / current * 100 if current else 0.0
            if ab_count >= dimension_rules.ab_count or (
                current >= dimension_rules.ab_min_total and ratio >= dimension_rules.ab_ratio
            ):
                related = sorted(
                    (
                        (sequence[index], str(category))
                        for category, sequence in category_ab_series.items()
                        if sequence[index] > 0
                    ),
                    key=lambda item: (-item[0], item[1]),
                )
                detail = (
                    f"本期A/B级{ab_count}条，占比{ratio:.1f}%"
                    f"（隐患总量{current}条）"
                )
                if include_category_details:
                    if related:
                        detail += "。A/B级类别明细：" + "；".join(
                            f"{category}{count}条" for count, category in related
                        )
                    else:
                        detail += "。未取得A/B级二级隐患类别明细"
                evidence.append(RiskEvidence(
                    "ab", "A/B级异常",
                    detail, True,
                    tuple(category for _count, category in related),
                    tuple((category, int(count)) for count, category in related),
                ))
        return evidence

    def _repeat_evidence(self, index, category_series, unit_rules):
        if not unit_rules.repeat_enabled:
            return None
        start = index - unit_rules.repeat_periods + 1
        if start < 0:
            return None
        hits = []
        for category, sequence in category_series.items():
            recent = sequence[start:index + 1]
            if len(recent) == unit_rules.repeat_periods and all(
                later > earlier for earlier, later in zip(recent, recent[1:])
            ):
                hits.append((recent[-1], str(category), recent))
        if not hits:
            return None
        hits.sort(key=lambda item: (-item[0], item[1]))
        detail = "；".join(
            f"“{category}”隐患连续{unit_rules.repeat_periods}期上升："
            + "→".join(f"{value}条" for value in recent)
            for _current, category, recent in hits
        )
        return RiskEvidence(
            "repeat", "重复发生", detail,
            related_categories=tuple(category for _current, category, _recent in hits),
        )

    def _area_category_evidence(self, index, category_series, category_units, rules):
        evidence = []
        if getattr(rules, "category_continuous_enabled", False):
            start = index - rules.category_continuous_periods + 1
            hits = []
            if start >= 0:
                for category, sequence in category_series.items():
                    recent = sequence[start:index + 1]
                    if len(recent) != rules.category_continuous_periods or not all(
                        later > earlier for earlier, later in zip(recent, recent[1:])
                    ):
                        continue
                    increase = recent[-1] - recent[0]
                    rate = None if recent[0] == 0 else increase / recent[0] * 100
                    if increase >= rules.category_continuous_absolute and (
                        recent[0] == 0 or rate >= rules.category_continuous_rate
                    ):
                        hits.append((recent[-1], str(category), recent, rate))
            if hits:
                hits.sort(key=lambda item: (-item[0], item[1]))
                detail = "；".join(
                    f"“{category}”最近{rules.category_continuous_periods}期严格上升："
                    + "→".join(f"{value}条" for value in recent)
                    + ("，起始值为0" if rate is None else f"，首末增长{rate:.1f}%")
                    for _current, category, recent, rate in hits
                )
                evidence.append(RiskEvidence(
                    "area_category_continuous", "区域二级隐患连续恶化", detail,
                    related_categories=tuple(item[1] for item in hits),
                ))

        if getattr(rules, "category_surge_enabled", False) and index >= 1:
            hits = []
            for category, sequence in category_series.items():
                previous, current = sequence[index - 1:index + 1]
                increase = current - previous
                rate = None if previous == 0 else increase / previous * 100
                if increase >= rules.category_surge_absolute and (
                    (previous == 0 and current >= rules.category_surge_absolute)
                    or (rate is not None and rate >= rules.category_surge_rate)
                ):
                    hits.append((increase, str(category), previous, current, rate))
            if hits:
                hits.sort(key=lambda item: (-item[0], item[1]))
                detail = "；".join(
                    f"“{category}”由{previous}条增至{current}条，"
                    + ("上期为0" if rate is None else f"上升{rate:.1f}%")
                    + f"、增加{increase}条"
                    for increase, category, previous, current, rate in hits
                )
                evidence.append(RiskEvidence(
                    "area_category_surge", "区域二级隐患突增", detail,
                    related_categories=tuple(item[1] for item in hits),
                ))

        if getattr(rules, "spread_enabled", False) and index >= 1:
            hits = []
            for category, unit_periods in category_units.items():
                if index >= len(unit_periods):
                    continue
                previous_units = unit_periods[index - 1]
                current_units = unit_periods[index]
                unit_increase = len(current_units) - len(previous_units)
                sequence = category_series.get(category, [])
                current_count = sequence[index] if index < len(sequence) else 0
                if (len(current_units) >= rules.spread_min_units
                        and unit_increase >= rules.spread_unit_increase
                        and current_count >= rules.spread_min_count):
                    hits.append((
                        len(current_units), str(category), len(previous_units),
                        current_count, tuple(sorted(str(unit) for unit in current_units)),
                    ))
            if hits:
                hits.sort(key=lambda item: (-item[0], -item[3], item[1]))
                detail_parts = []
                for current_units, category, previous_units, current_count, units in hits:
                    shown = "、".join(units[:5])
                    suffix = f"等{len(units)}家" if len(units) > 5 else ""
                    detail_parts.append(
                        f"“{category}”本期涉及{current_units}家责任单位"
                        f"（上期{previous_units}家、增加{current_units - previous_units}家），"
                        f"共{current_count}条：{shown}{suffix}"
                    )
                evidence.append(RiskEvidence(
                    "area_spread", "区域风险跨单位扩散", "；".join(detail_parts), True,
                    tuple(item[1] for item in hits),
                ))
        return evidence

    def _brake_evidence(self, unit, index, brake_series, brake_categories,
                        hazard_categories, uncategorized_brakes, category_ready,
                        unit_rules):
        evidence = []
        sequence = brake_series.get(unit, [])
        if unit_rules.brake_repeat_enabled:
            start = index - unit_rules.brake_repeat_periods + 1
            if start >= 0:
                details = []
                related = set()
                category_hits = []
                for category, category_sequence in brake_categories.get(unit, {}).items():
                    recent = category_sequence[start:index + 1]
                    if len(recent) == unit_rules.brake_repeat_periods and all(
                        value > 0 for value in recent
                    ):
                        category_hits.append((sum(recent), str(category), recent))
                category_hits.sort(key=lambda item: (-item[0], item[1]))
                if category_hits:
                    hazard_names = set(hazard_categories.get(unit, {}))
                    related.update(
                        category for _total, category, _recent in category_hits
                        if category in hazard_names
                    )
                    details.append("；".join(
                        f"“{category}”（预警问题类别）连续"
                        f"{unit_rules.brake_repeat_periods}期收到："
                        + "→".join(f"{value}次" for value in recent)
                        + (
                            "" if category in hazard_names else
                            "，未匹配到同名隐患二级分类，暂不展示趋势"
                        )
                        for _total, category, recent in category_hits
                    ))
                recent_total = sequence[start:index + 1] if sequence else []
                if len(recent_total) == unit_rules.brake_repeat_periods and all(
                    later > earlier
                    for earlier, later in zip(recent_total, recent_total[1:])
                ):
                    current_problem_categories = sorted(
                        str(category)
                        for category, category_sequence
                        in brake_categories.get(unit, {}).items()
                        if category_sequence[index] > 0
                    )
                    hazard_names = set(hazard_categories.get(unit, {}))
                    related.update(
                        category for category in current_problem_categories
                        if category in hazard_names
                    )
                    total_detail = (
                        f"预警刹车总量连续{unit_rules.brake_repeat_periods}期上升："
                        + "→".join(f"{value}次" for value in recent_total)
                    )
                    if current_problem_categories:
                        category_details = "、".join(
                            f"“{category}”（预警问题类别）"
                            + (
                                "" if category in hazard_names else
                                "，未匹配到同名隐患二级分类，暂不展示趋势"
                            )
                            for category in current_problem_categories
                        )
                        total_detail += f"；本期预警问题类别：{category_details}"
                    details.append(total_detail)
                if details:
                    evidence.append(RiskEvidence(
                        "brake_repeat", "重复预警刹车", "；".join(details), True,
                        tuple(sorted(related)),
                    ))
        if unit_rules.missed_warning_enabled and category_ready and index >= 1:
            uncategorized = uncategorized_brakes.get(unit, [])
            if index >= len(uncategorized) or uncategorized[index] == 0:
                missed = []
                for category, hazard_sequence in hazard_categories.get(unit, {}).items():
                    previous, current = hazard_sequence[index - 1:index + 1]
                    increase = current - previous
                    rate = None if previous == 0 else increase / previous * 100
                    triggered = increase >= unit_rules.missed_warning_absolute and (
                        (previous == 0 and current >= unit_rules.missed_warning_absolute)
                        or (rate is not None and rate >= unit_rules.missed_warning_rate)
                    )
                    brake_sequence = brake_categories.get(unit, {}).get(category, [])
                    issued = index < len(brake_sequence) and brake_sequence[index] > 0
                    if triggered and not issued:
                        missed.append((increase, str(category), previous, current, rate))
                missed.sort(key=lambda item: (-item[0], item[1]))
                if missed:
                    detail = "；".join(
                        f"“{category}”隐患由{previous}条增至{current}条，"
                        + ("上期为0" if rate is None else f"上升{rate:.1f}%")
                        + f"、增加{increase}条，本期未发现同类别预警刹车"
                        for increase, category, previous, current, rate in missed
                    )
                    evidence.append(RiskEvidence(
                        "missed_warning", "隐患增多可能未及时预警", detail, True,
                        tuple(category for _increase, category, *_rest in missed),
                    ))
        return evidence

    def _dimension_category_maps(self, hazard, dimension, axis, period_type):
        result = defaultdict(dict)
        required = [dimension, self.cfg.col_category]
        if hazard.empty or any(column not in hazard.columns for column in required):
            return result
        data = self.preprocessor.with_second_category(hazard)
        data = self._clean_dimension(data, dimension)
        data = self._clean_dimension(data, self.preprocessor.SECOND_CATEGORY_COL)
        if data.empty:
            return result
        data["周期开始日期"] = period_starts(data[self.cfg.col_date], period_type)
        grouped = data.groupby([
            "周期开始日期", dimension, self.preprocessor.SECOND_CATEGORY_COL,
        ]).size()
        axis_index = {point: index for index, point in enumerate(axis)}
        for (point, owner, category), count in grouped.items():
            if point in axis_index:
                sequence = result[str(owner)].setdefault(str(category), [0] * len(axis))
                sequence[axis_index[point]] = int(count)
        return result

    def _hazard_category_maps(self, hazard, axis, period_type):
        return self._dimension_category_maps(
            hazard, self.cfg.col_unit, axis, period_type
        )

    def _area_category_unit_maps(self, area_frame, axis, period_type):
        result = defaultdict(dict)
        area_column = self.preprocessor.MAIN_AREA_COL
        required = [area_column, self.cfg.col_unit, self.cfg.col_category]
        if area_frame.empty or any(column not in area_frame.columns for column in required):
            return result
        data = self.preprocessor.with_second_category(area_frame)
        for column in (area_column, self.cfg.col_unit, self.preprocessor.SECOND_CATEGORY_COL):
            data = self._clean_dimension(data, column)
        if data.empty:
            return result
        data["周期开始日期"] = period_starts(data[self.cfg.col_date], period_type)
        grouped = data.groupby([
            "周期开始日期", area_column, self.preprocessor.SECOND_CATEGORY_COL,
        ])[self.cfg.col_unit].unique()
        axis_index = {point: index for index, point in enumerate(axis)}
        for (point, area, category), units in grouped.items():
            if point not in axis_index:
                continue
            periods = result[str(area)].setdefault(
                str(category), [set() for _point in axis]
            )
            periods[axis_index[point]] = {
                str(unit).strip() for unit in units if str(unit).strip()
            }
        return result

    def _brake_maps(self, brake, axis, period_type):
        series = self._series_for_axis(brake, "发出日期", "责任单位", axis, period_type)
        category_maps = defaultdict(dict)
        uncategorized = defaultdict(lambda: [0] * len(axis))
        data = self._clean_dimension(brake, "责任单位")
        if data.empty or "问题类别" not in data.columns:
            return series, category_maps, uncategorized, False
        data = data.reset_index(drop=True)
        data["_记录序号"] = data.index
        data["周期开始日期"] = period_starts(data["发出日期"], period_type)
        axis_index = {point: index for index, point in enumerate(axis)}
        raw = data["问题类别"].fillna("").astype(str).str.strip()
        missing = data[raw.eq("")]
        for (point, unit), count in missing.groupby(["周期开始日期", "责任单位"]).size().items():
            if point in axis_index:
                uncategorized[str(unit)][axis_index[point]] = int(count)
        categorized = data[raw.ne("")].copy()
        if categorized.empty:
            return series, category_maps, uncategorized, False
        categorized["预警问题类别"] = (
            categorized["问题类别"].astype(str).str.split(r"[,，、;；]+", regex=True)
        )
        categorized = categorized.explode("预警问题类别")
        categorized["预警问题类别"] = categorized["预警问题类别"].astype(str).str.strip()
        categorized = categorized[categorized["预警问题类别"].ne("")]
        categorized = categorized.drop_duplicates(["_记录序号", "预警问题类别"])
        grouped = categorized.groupby([
            "周期开始日期", "责任单位", "预警问题类别",
        ]).size()
        for (point, unit, category), count in grouped.items():
            if point in axis_index:
                sequence = category_maps[str(unit)].setdefault(str(category), [0] * len(axis))
                sequence[axis_index[point]] = int(count)
        return series, category_maps, uncategorized, bool(category_maps)

    def _ab_series(self, data, dimension, axis, period_type):
        data = self._clean_dimension(data, dimension)
        if data.empty or self.cfg.col_level not in data.columns:
            return {}
        levels = data[self.cfg.col_level].astype(str).str.strip().str.upper()
        levels = levels.str.replace("级", "", regex=False)
        ab = data[levels.isin(["A", "B"])].copy()
        return self._series_for_axis(ab, self.cfg.col_date, dimension, axis, period_type)

    @staticmethod
    def _related_category_series(evidence, available):
        related = {
            category
            for item in evidence
            for category in item.related_categories
        }
        selected = [
            (str(category), tuple(sequence))
            for category, sequence in available.items()
            if str(category) in related
        ]
        selected.sort(key=lambda item: (-sum(item[1]), item[0]))
        return tuple(selected)

    def _build_section(self, kind, frame, dimension, full_axis, full_labels,
                       complete_axis, complete_labels, rules, period_type,
                       hazard_categories, full_hazard_categories,
                       hazard_ab_categories, brake_series, brake_categories,
                       uncategorized_brakes, brake_category_ready,
                       area_category_units=None):
        if not complete_axis:
            return AlertSection(message="所选时间段内没有完整周期，暂不生成预警")
        full_series = self._series_for_axis(
            frame, self.cfg.col_date, dimension, full_axis, period_type
        )
        complete_series = self._series_for_axis(
            frame, self.cfg.col_date, dimension, complete_axis, period_type
        )
        ab_series = self._ab_series(frame, dimension, complete_axis, period_type)
        dimension_rules = rules.for_kind(kind)
        area_category_units = area_category_units or {}
        current_items, improved_items = [], []
        for name, values in complete_series.items():
            ab_values = ab_series.get(name, [0] * len(complete_axis))
            history = []
            for index, label in enumerate(complete_labels):
                evidence = self._basic_evidence(
                    values, ab_values, index, dimension_rules, period_type,
                    hazard_categories.get(name, {}) if kind in ("unit", "area") else {},
                    hazard_ab_categories.get(name, {}) if kind in ("unit", "area") else {},
                    include_category_details=kind in ("unit", "area"),
                )
                if kind == "unit":
                    repeat = self._repeat_evidence(
                        index, hazard_categories.get(name, {}), rules.unit
                    )
                    if repeat:
                        evidence.append(repeat)
                    evidence.extend(self._brake_evidence(
                        name, index, brake_series, brake_categories,
                        hazard_categories, uncategorized_brakes,
                        brake_category_ready, rules.unit,
                    ))
                elif kind == "area":
                    evidence.extend(self._area_category_evidence(
                        index, hazard_categories.get(name, {}),
                        area_category_units.get(name, {}), rules.area,
                    ))
                if evidence:
                    history.append(PeriodRisk(
                        label, self._risk_level(evidence), tuple(evidence)
                    ))
            if not history:
                continue
            current = next((item for item in history if item.period == complete_labels[-1]), None)
            previous_triggered = any(
                item.period == complete_labels[-2] for item in history
            ) if len(complete_labels) >= 2 else False
            full_values = full_series.get(name, [0] * len(full_axis))
            if current:
                status = "持续" if previous_triggered else "新增"
                category_series = self._related_category_series(
                    current.evidence, full_hazard_categories.get(name, {})
                ) if kind == "unit" else ()
                current_items.append(RiskObject(
                    kind, name, current.level, status, complete_labels[-1],
                    current.evidence, tuple(full_labels), tuple(full_values),
                    tuple(history), current.period, category_series,
                ))
            else:
                last = history[-1]
                category_series = self._related_category_series(
                    last.evidence, full_hazard_categories.get(name, {})
                ) if kind == "unit" else ()
                improved_items.append(RiskObject(
                    kind, name, last.level, "已改善", complete_labels[-1],
                    last.evidence, tuple(full_labels), tuple(full_values),
                    tuple(history), last.period, category_series,
                ))
        current_items.sort(key=lambda item: (
            self.LEVEL_ORDER[item.level], -len(item.evidence), item.name
        ))
        improved_items.sort(key=lambda item: item.name)
        message = "" if current_items or improved_items else "当前及历史完整周期均未命中预警规则"
        return AlertSection(current_items, improved_items, message)

    def alerts(self, hazard_df, brake_df, start, end, period_type="week", rules=None):
        start, end = self.validate_range(hazard_df, brake_df, start, end)
        rules = rules or self.rule_repository.load()
        hazard = self._hazard_data(hazard_df, start, end)
        brake = self._brake_data(brake_df, start, end)
        full_axis, full_labels = self._axis(start, end, period_type)
        complete_axis, complete_labels, excluded = self._complete_axis(start, end, period_type)
        if hazard_df is None or hazard_df.empty:
            message = "请先在隐患分析中加载数据"
            empty = AlertSection(message=message)
            return AlertResult(
                empty, AlertSection(message=message), AlertSection(message=message),
                complete_labels[-1] if complete_labels else "", excluded,
                f"v{rules.schema_version}", [], [], message,
            )
        if hazard.empty:
            message = "所选时间段内没有可统计的隐患数据"
            return AlertResult(
                AlertSection(message=message), AlertSection(message=message),
                AlertSection(message=message), complete_labels[-1] if complete_labels else "",
                excluded, f"v{rules.schema_version}", [], [], message,
            )

        unit_frame = self._clean_dimension(hazard, self.cfg.col_unit)
        area_frame = self.preprocessor.with_main_area(hazard)
        special_frame = self.preprocessor.with_second_category(hazard)
        hazard_categories = self._hazard_category_maps(
            hazard, complete_axis, period_type
        )
        full_hazard_categories = self._hazard_category_maps(
            hazard, full_axis, period_type
        )
        if self.cfg.col_level in hazard.columns:
            levels = hazard[self.cfg.col_level].astype(str).str.strip().str.upper()
            levels = levels.str.replace("级", "", regex=False)
            ab_hazard = hazard[levels.isin(["A", "B"])].copy()
        else:
            ab_hazard = hazard.iloc[0:0].copy()
        hazard_ab_categories = self._hazard_category_maps(
            ab_hazard, complete_axis, period_type
        )
        area_categories = self._dimension_category_maps(
            area_frame, self.preprocessor.MAIN_AREA_COL, complete_axis, period_type
        )
        full_area_categories = self._dimension_category_maps(
            area_frame, self.preprocessor.MAIN_AREA_COL, full_axis, period_type
        )
        area_ab_categories = self._dimension_category_maps(
            self.preprocessor.with_main_area(ab_hazard),
            self.preprocessor.MAIN_AREA_COL, complete_axis, period_type,
        )
        area_category_units = self._area_category_unit_maps(
            area_frame, complete_axis, period_type
        )
        brake_series, brake_categories, uncategorized_brakes, category_ready = (
            self._brake_maps(brake, complete_axis, period_type)
        )
        category_ready = bool(
            brake_df is not None
            and not brake_df.empty
            and "问题类别" in brake_df.columns
            and brake_df["问题类别"].notna().any()
            and brake_df["问题类别"].fillna("").astype(str).str.strip().ne("").any()
        )
        hazard_units = set(unit_frame[self.cfg.col_unit].astype(str)) if not unit_frame.empty else set()
        unmatched = sorted(set(brake_series) - hazard_units)
        effect_pending = []
        if rules.unit.missed_warning_enabled:
            if brake_df is None or brake_df.empty:
                effect_pending.append("未加载预警刹车数据，已跳过未及时预警规则")
            elif "问题类别" not in brake_df.columns:
                effect_pending.append("预警刹车数据缺少“问题类别”字段，已跳过未及时预警规则")
            elif not category_ready:
                effect_pending.append("所选时间段内“问题类别”无法解析，已跳过未及时预警规则")
            elif complete_axis:
                latest = len(complete_axis) - 1
                uncertain = sorted(
                    unit for unit, sequence in uncategorized_brakes.items()
                    if sequence[latest] > 0 and unit in hazard_units
                )
                if uncertain:
                    effect_pending.append(
                        "以下单位本期存在未填写问题类别的预警刹车，已跳过其漏发判断："
                        + "、".join(uncertain)
                    )

        sections = [
            self._build_section(
                "unit", unit_frame, self.cfg.col_unit, full_axis, full_labels,
                complete_axis, complete_labels, rules, period_type,
                hazard_categories, full_hazard_categories, hazard_ab_categories,
                brake_series, brake_categories,
                uncategorized_brakes, category_ready, {},
            ),
            self._build_section(
                "area", area_frame, self.preprocessor.MAIN_AREA_COL, full_axis, full_labels,
                complete_axis, complete_labels, rules, period_type,
                area_categories, full_area_categories, area_ab_categories,
                {}, {}, {}, False, area_category_units,
            ),
            self._build_section(
                "special", special_frame, self.preprocessor.SECOND_CATEGORY_COL,
                full_axis, full_labels, complete_axis, complete_labels, rules,
                period_type, {}, {}, {}, {}, {}, {}, False, {},
            ),
        ]
        message = ""
        if len(complete_axis) < 2:
            message = "完整周期数量较少，仅执行具备数据条件的规则"
        return AlertResult(
            *sections,
            current_period=complete_labels[-1] if complete_labels else "",
            excluded_periods=excluded,
            rule_version=f"v{rules.schema_version}",
            unmatched_units=unmatched,
            effect_pending=effect_pending,
            message=message,
        )
