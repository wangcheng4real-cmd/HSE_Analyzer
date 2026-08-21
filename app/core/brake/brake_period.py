import pandas as pd


PERIOD_TYPES = {"week", "month", "quarter"}


def period_starts(dates, period_type):
    if period_type not in PERIOD_TYPES:
        raise ValueError(f"不支持的统计周期：{period_type}")
    dates = pd.to_datetime(dates, errors="coerce").dt.normalize()
    if period_type == "week":
        return dates - pd.to_timedelta(dates.dt.weekday, unit="D")
    if period_type == "month":
        return dates.dt.to_period("M").dt.start_time
    return dates.dt.to_period("Q").dt.start_time


def complete_periods(first, last, period_type):
    frequency = {"week": "7D", "month": "MS", "quarter": "QS"}[period_type]
    return pd.date_range(first, last, freq=frequency)


def period_label(start, period_type):
    if period_type == "week":
        return f"{start:%Y-%m-%d}至{start + pd.Timedelta(days=6):%Y-%m-%d}"
    if period_type == "month":
        return f"{start:%Y年%m月}"
    quarter = (start.month - 1) // 3 + 1
    return f"{start.year}年第{quarter}季度"


def period_axis(starts, period_type):
    periods = complete_periods(starts.min(), starts.max(), period_type)
    return periods, [period_label(value, period_type) for value in periods]
