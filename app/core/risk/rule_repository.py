from dataclasses import asdict, dataclass, field, fields
import json
import os
from pathlib import Path
import shutil
import sys


BOOLEAN_FIELDS = {"baseline_enabled", "continuous_enabled", "ab_enabled"}
PERCENTAGE_FIELDS = {"baseline_rate", "continuous_rate", "ab_ratio"}
AREA_BOOLEAN_FIELDS = {
    "category_continuous_enabled", "category_surge_enabled", "spread_enabled",
}
AREA_PERCENTAGE_FIELDS = {"category_continuous_rate", "category_surge_rate"}


def _parse_fields(model, values, boolean_fields, percentage_fields):
    defaults = model()
    values = dict(values or {})
    parsed = {}
    for item in fields(model):
        name = item.name
        raw = values.get(name, getattr(defaults, name))
        if name in boolean_fields:
            parsed[name] = (
                raw.strip().lower() in {"1", "true", "yes", "on"}
                if isinstance(raw, str) else bool(raw)
            )
        elif name in percentage_fields:
            value = float(raw)
            if value < 0 or value > 10000:
                raise ValueError(f"{name}必须在0到10000之间")
            parsed[name] = value
        else:
            value = int(raw)
            if value <= 0:
                raise ValueError(f"{name}必须为正整数")
            parsed[name] = value
    return model(**parsed)


@dataclass(frozen=True)
class DimensionRiskRules:
    baseline_enabled: bool = True
    baseline_week_window: int = 3
    baseline_month_window: int = 3
    baseline_quarter_window: int = 2
    baseline_rate: float = 30.0
    baseline_absolute: int = 5

    continuous_enabled: bool = True
    continuous_periods: int = 3
    continuous_rate: float = 30.0
    continuous_absolute: int = 5

    ab_enabled: bool = True
    ab_count: int = 5
    ab_ratio: float = 20.0
    ab_min_total: int = 10

    @classmethod
    def from_mapping(cls, values):
        return _parse_fields(cls, values, BOOLEAN_FIELDS, PERCENTAGE_FIELDS)


@dataclass(frozen=True)
class UnitRiskRules(DimensionRiskRules):
    repeat_enabled: bool = True
    repeat_periods: int = 3

    brake_repeat_enabled: bool = True
    brake_repeat_periods: int = 3

    missed_warning_enabled: bool = True
    missed_warning_rate: float = 50.0
    missed_warning_absolute: int = 5

    @classmethod
    def from_mapping(cls, values):
        return _parse_fields(
            cls, values,
            BOOLEAN_FIELDS | {
                "repeat_enabled", "brake_repeat_enabled", "missed_warning_enabled",
            },
            PERCENTAGE_FIELDS | {"missed_warning_rate"},
        )


@dataclass(frozen=True)
class AreaRiskRules(DimensionRiskRules):
    category_continuous_enabled: bool = True
    category_continuous_periods: int = 3
    category_continuous_rate: float = 30.0
    category_continuous_absolute: int = 5

    category_surge_enabled: bool = True
    category_surge_rate: float = 50.0
    category_surge_absolute: int = 5

    spread_enabled: bool = True
    spread_min_units: int = 3
    spread_unit_increase: int = 2
    spread_min_count: int = 5

    @classmethod
    def from_mapping(cls, values):
        return _parse_fields(
            cls, values,
            BOOLEAN_FIELDS | AREA_BOOLEAN_FIELDS,
            PERCENTAGE_FIELDS | AREA_PERCENTAGE_FIELDS,
        )


@dataclass(frozen=True)
class RiskRules:
    schema_version: int = 5
    unit: UnitRiskRules = field(default_factory=UnitRiskRules)
    area: AreaRiskRules = field(default_factory=AreaRiskRules)
    special: DimensionRiskRules = field(default_factory=DimensionRiskRules)

    def for_kind(self, kind):
        try:
            return {"unit": self.unit, "area": self.area, "special": self.special}[kind]
        except KeyError as exc:
            raise ValueError(f"未知预警维度：{kind}") from exc

    @staticmethod
    def _legacy_dimension(values, kind):
        return {
            "baseline_enabled": values.get("baseline_enabled", True),
            "baseline_week_window": values.get("baseline_week_window", 3),
            "baseline_month_window": values.get("baseline_month_window", 3),
            "baseline_quarter_window": values.get("baseline_quarter_window", 2),
            "baseline_rate": values.get(f"{kind}_rate", 30.0),
            "baseline_absolute": values.get(f"{kind}_absolute", 5),
            "continuous_enabled": values.get("continuous_enabled", True),
            "continuous_periods": values.get("continuous_periods", 3),
            "continuous_rate": values.get("continuous_rate", 30.0),
            "continuous_absolute": values.get("continuous_absolute", 5),
            "ab_enabled": values.get("ab_enabled", True),
            "ab_count": values.get("ab_count", 5),
            "ab_ratio": values.get("ab_ratio", 20.0),
            "ab_min_total": values.get("ab_min_total", 10),
        }

    @classmethod
    def from_mapping(cls, values):
        values = dict(values or {})
        try:
            source_version = int(values.get("schema_version", 2))
        except (TypeError, ValueError):
            source_version = 2
        if source_version >= 4:
            if not all(name in values for name in ("unit", "area", "special")):
                raise ValueError("v4规则配置必须包含unit、area和special")
            return cls(
                schema_version=max(5, source_version),
                unit=UnitRiskRules.from_mapping(values["unit"]),
                area=AreaRiskRules.from_mapping(values["area"]),
                special=DimensionRiskRules.from_mapping(values["special"]),
            )

        # v1/v2 first adopted the v3 enablement policy, then all shared v3
        # values are copied into independent v4 dimensions.
        if source_version < 3:
            for name in (
                "baseline_enabled", "continuous_enabled", "ab_enabled",
                "repeat_enabled", "brake_repeat_enabled", "missed_warning_enabled",
            ):
                values[name] = True
        unit_values = cls._legacy_dimension(values, "unit")
        unit_values.update({
            "repeat_enabled": values.get("repeat_enabled", True),
            "repeat_periods": values.get("repeat_periods", 3),
            "brake_repeat_enabled": values.get("brake_repeat_enabled", True),
            "brake_repeat_periods": values.get("brake_repeat_periods", 3),
            "missed_warning_enabled": values.get("missed_warning_enabled", True),
            "missed_warning_rate": values.get("missed_warning_rate", 50.0),
            "missed_warning_absolute": values.get("missed_warning_absolute", 5),
        })
        return cls(
            unit=UnitRiskRules.from_mapping(unit_values),
            area=AreaRiskRules.from_mapping(cls._legacy_dimension(values, "area")),
            special=DimensionRiskRules.from_mapping(cls._legacy_dimension(values, "special")),
        )


class RiskRuleRepository:
    """保存可解释预警规则，并兼容v1-v4配置。"""

    def __init__(self, path=None):
        self._explicit_path = path is not None
        self.path = Path(path) if path else self._default_path()
        self.revision = 0
        self.last_error = ""
        try:
            self._initialize_packaged_config()
        except OSError as exc:
            self.last_error = f"预警规则初始配置创建失败，已使用默认值：{exc}"

    @staticmethod
    def _default_path():
        if getattr(sys, "frozen", False):
            local_app_data = os.environ.get("LOCALAPPDATA")
            root = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
            return root / "HSE数据分析平台" / "config" / "risk_rules.json"
        project_root = Path(__file__).resolve().parents[3]
        return project_root / "config" / "risk_rules.json"

    def _initialize_packaged_config(self):
        if self._explicit_path or self.path.exists() or not getattr(sys, "frozen", False):
            return
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        bundled_config = bundle_root / "config" / "risk_rules.json"
        if not bundled_config.exists():
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled_config, self.path)

    def load(self):
        self.last_error = ""
        try:
            self._initialize_packaged_config()
        except OSError as exc:
            self.last_error = f"预警规则初始配置创建失败，已使用默认值：{exc}"
        if not self.path.exists():
            return RiskRules()
        try:
            with self.path.open("r", encoding="utf-8") as source:
                return RiskRules.from_mapping(json.load(source))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self.last_error = f"预警规则配置读取失败，已使用默认值：{exc}"
            return RiskRules()

    def save(self, rules):
        if not isinstance(rules, RiskRules):
            rules = RiskRules.from_mapping(rules)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as target:
            json.dump(asdict(rules), target, ensure_ascii=False, indent=2)
        temporary.replace(self.path)
        self.revision += 1
        self.last_error = ""
        return rules
