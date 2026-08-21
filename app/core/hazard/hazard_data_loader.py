import os

import pandas as pd

from app.core.background_task import TaskCancelled


class HazardDataLoader:

    DATE_COLUMN = "检查日期"
    PERIOD_COLUMN = "时间周期"
    PERIOD_START_COLUMN = "周期开始日期"
    PERIOD_TYPES = {"week", "month", "quarter"}

    def __init__(self):
        self.files = []
        self.invalid_date_count = 0

    def _is_duplicate(self, file_path):
        target = os.path.normcase(os.path.abspath(file_path))
        return any(
            os.path.normcase(os.path.abspath(item["path"])) == target
            for item in self.files
        )

    def add_files(self, file_paths):
        added = 0
        skipped = []

        for file_path in file_paths:
            if self._is_duplicate(file_path):
                skipped.append(os.path.basename(file_path))
                continue
            self.files.append({
                "path": file_path,
                "name": os.path.basename(file_path)
            })
            added += 1

        return added, skipped

    def remove_file(self, index):
        if 0 <= index < len(self.files):
            del self.files[index]

    def clear(self):
        self.files.clear()
        self.invalid_date_count = 0

    def get_file_list(self):
        return [dict(item) for item in self.files]

    def get_total_file_count(self):
        return len(self.files)

    def read_file(self, item):
        try:
            df = pd.read_excel(item["path"])
        except Exception as exc:
            raise ValueError(f"无法读取Excel文件：{item['name']}\n{exc}") from exc

        df.columns = df.columns.astype(str).str.strip()
        if self.DATE_COLUMN not in df.columns:
            raise ValueError(
                f"文件缺少“{self.DATE_COLUMN}”字段：{item['name']}"
            )

        df = df.copy()
        parsed_date = pd.to_datetime(df[self.DATE_COLUMN], errors="coerce")
        invalid_count = int(parsed_date.isna().sum())
        df = df.loc[parsed_date.notna()].copy()
        parsed_date = parsed_date.loc[parsed_date.notna()].dt.normalize()

        df[self.DATE_COLUMN] = parsed_date
        df["文件名"] = item["name"]
        return df, invalid_count

    def group_by_period(self, df_all, period_type="week"):
        if period_type not in self.PERIOD_TYPES:
            raise ValueError(f"不支持的统计周期：{period_type}")
        if df_all is None or df_all.empty:
            return pd.DataFrame(), []

        df = df_all.copy()
        df = df.drop(
            columns=[self.PERIOD_COLUMN, self.PERIOD_START_COLUMN],
            errors="ignore"
        )
        dates = pd.to_datetime(df[self.DATE_COLUMN], errors="coerce").dt.normalize()
        df[self.DATE_COLUMN] = dates

        if period_type == "week":
            starts = dates - pd.to_timedelta(dates.dt.weekday, unit="D")
            ends = starts + pd.Timedelta(days=6)
            labels = starts.dt.strftime("%Y-%m-%d") + " 至 " + ends.dt.strftime("%Y-%m-%d")
        elif period_type == "month":
            starts = dates.dt.to_period("M").dt.start_time
            labels = starts.dt.strftime("%Y年%m月")
        else:
            quarters = dates.dt.to_period("Q")
            starts = quarters.dt.start_time
            labels = (
                starts.dt.year.astype(str)
                + "年第"
                + quarters.dt.quarter.astype(str)
                + "季度"
            )

        df[self.PERIOD_START_COLUMN] = starts
        df[self.PERIOD_COLUMN] = labels
        df = df.sort_values(
            [self.PERIOD_START_COLUMN, self.DATE_COLUMN], kind="stable"
        ).reset_index(drop=True)
        groups = [
            group.reset_index(drop=True)
            for _, group in df.groupby(self.PERIOD_START_COLUMN, sort=True)
        ]
        return df, groups

    def load(self, progress_callback=None, period_type="week", cancel_event=None):
        if not self.files:
            self.invalid_date_count = 0
            return pd.DataFrame(), []

        data_list = []
        invalid_date_count = 0
        total = len(self.files)

        # 先全部读取成功，再更新加载结果，避免产生半套数据。
        for index, item in enumerate(self.files, start=1):
            if cancel_event is not None and cancel_event.is_set():
                raise TaskCancelled("隐患数据加载已取消")
            df, invalid_count = self.read_file(item)
            data_list.append(df)
            invalid_date_count += invalid_count
            if progress_callback:
                progress_callback(index, total, item["path"])
            if cancel_event is not None and cancel_event.is_set():
                raise TaskCancelled("隐患数据加载已取消")

        valid_frames = [df for df in data_list if not df.empty]
        if valid_frames:
            raw_all = pd.concat(valid_frames, ignore_index=True)
            df_all, df_list = self.group_by_period(raw_all, period_type)
        else:
            df_all = pd.DataFrame()
            df_list = []

        self.invalid_date_count = invalid_date_count
        return df_all, df_list

