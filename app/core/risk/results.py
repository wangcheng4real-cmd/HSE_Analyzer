from dataclasses import dataclass, field


@dataclass(frozen=True)
class DateBounds:
    start: object = None
    end: object = None

    @property
    def empty(self):
        return self.start is None or self.end is None


@dataclass
class MultiSeriesResult:
    periods: list = field(default_factory=list)
    series: dict = field(default_factory=dict)


@dataclass
class TrendResult:
    periods: list = field(default_factory=list)
    values: list = field(default_factory=list)


@dataclass
class DashboardResult:
    hazard_levels: dict = field(default_factory=dict)
    hazard_trend: TrendResult = field(default_factory=TrendResult)
    brake_types: dict = field(default_factory=dict)
    brake_trend: TrendResult = field(default_factory=TrendResult)
    hazard_message: str = ""
    brake_message: str = ""


@dataclass(frozen=True)
class RiskEvidence:
    code: str
    title: str
    detail: str
    severe: bool = False
    related_categories: tuple = field(default_factory=tuple)
    related_category_counts: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class PeriodRisk:
    period: str
    level: str
    evidence: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class RiskObject:
    kind: str
    name: str
    level: str
    status: str
    current_period: str
    evidence: tuple
    periods: tuple
    counts: tuple
    history: tuple = field(default_factory=tuple)
    last_trigger_period: str = ""
    category_series: tuple = field(default_factory=tuple)

    @property
    def related_category_names(self):
        """最终可展示趋势的二级隐患类别，顺序与 category_series 一致。"""
        return tuple(str(name) for name, _values in self.category_series)

    def related_category_summary(self, limit=5):
        """生成单位预警卡的类别摘要，UI 不再自行解析规则证据。"""
        if self.kind != "unit":
            return ""
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("类别摘要数量必须为正整数")
        names = self.related_category_names
        if not names:
            return "当前预警暂未归因到具体二级隐患类别"
        shown = "、".join(names[:limit])
        suffix = f"等{len(names)}类" if len(names) > limit else ""
        return f"涉及二级隐患：{shown}{suffix}"

    @property
    def evidence_summary(self):
        """卡片和单位详情共同使用的规则证据文案。"""
        if self.status == "已改善":
            return "最近触发证据：" + "；".join(
                evidence.detail for evidence in self.evidence
            )
        return "\n".join(
            f"• {evidence.title}：{evidence.detail}" for evidence in self.evidence
        )

    @property
    def detail_summary(self):
        """单位详情说明，内容与点击前预警卡保持一致。"""
        parts = [self.message]
        category_summary = self.related_category_summary()
        if category_summary:
            parts.append(category_summary)
        parts.append(f"当前周期：{self.current_period}")
        if self.evidence_summary:
            parts.append(self.evidence_summary)
        return "\n".join(parts)

    @property
    def message(self):
        kind_names = {"unit": "单位", "area": "区域", "special": "专项"}
        if self.status == "已改善":
            return (
                f"{self.name}{kind_names[self.kind]}已改善，最近触发周期为"
                f"{self.last_trigger_period}，当前周期未再命中规则"
            )
        return (
            f"{self.name}{kind_names[self.kind]}：{self.status}{self.level}预警，"
            f"命中{len(self.evidence)}条规则"
        )


@dataclass
class AlertSection:
    items: list = field(default_factory=list)
    improved: list = field(default_factory=list)
    message: str = ""


@dataclass
class AlertResult:
    units: AlertSection = field(default_factory=AlertSection)
    areas: AlertSection = field(default_factory=AlertSection)
    specials: AlertSection = field(default_factory=AlertSection)
    current_period: str = ""
    excluded_periods: list = field(default_factory=list)
    rule_version: str = "v2"
    unmatched_units: list = field(default_factory=list)
    effect_pending: list = field(default_factory=list)
    message: str = ""
