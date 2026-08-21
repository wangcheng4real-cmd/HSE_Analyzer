import os
import re

import pandas as pd

from app.core.background_task import TaskCancelled


class BrakeDataLoader:

    BRAKE_TYPES = ["通报批评", "整改通知", "挂牌督办", "管理约谈", "停工令"]

    UNIT_FIELD_BY_TYPE = {
        "停工令": "责任单位",
        "管理约谈": "被约谈方",
        "挂牌督办": "责任承包商",
        "通报批评": "责任承包商",
        "整改通知": "责任承包商",
    }

    DATE_FIELDS_BY_TYPE = {
        "停工令": ["发出日期", "发出日期(审批通过时间)", "发出日期（审批通过时间）"],
        "管理约谈": ["发出时间"],
        "挂牌督办": ["发出日期", "发出日期(审批通过时间)", "发出日期（审批通过时间）"],
        "通报批评": ["发出日期", "发出日期(审批通过时间)", "发出日期（审批通过时间）"],
        "整改通知": ["发出日期", "发出日期(审批通过时间)", "发出日期（审批通过时间）"],
    }

    FIELD_ALIASES = {
        "预警编号": ["编号", "约谈编号"],
        "主题": ["主题", "约谈主题"],
        "发出方": ["发出方"],
        "区域": ["涉及厂房"],
        "问题类别": ["问题类别"],
        "完成时间": ["完成时间"],
        "状态": ["状态"]
    }

    def __init__(self):
        self.files = []

    def _is_duplicate(self, file_path):
        target = os.path.normcase(os.path.abspath(file_path))
        return any(
            os.path.normcase(os.path.abspath(item["path"])) == target
            for item in self.files
        )

    def add_files(self, file_paths, cancel_event=None):
        added = 0
        skipped = []
        pending = []

        for file_path in file_paths:
            if cancel_event is not None and cancel_event.is_set():
                raise TaskCancelled("预警刹车文件识别已取消")
            if self._is_duplicate(file_path):
                skipped.append(os.path.basename(file_path))
                continue

            item = {
                "path": file_path,
                "name": os.path.basename(file_path),
                "预警刹车类型": "待识别",
                "status": "待识别",
                "rows": 0
            }

            # 上传后立即识别类型，界面可直接显示。
            try:
                metadata = self.inspect_file(file_path)
                item["预警刹车类型"] = metadata["预警刹车类型"]
                item["metadata"] = metadata
                item["status"] = "已识别"
            except Exception as exc:
                item["status"] = "识别失败"
                item["error"] = str(exc)

            pending.append(item)
            added += 1

        if cancel_event is not None and cancel_event.is_set():
            raise TaskCancelled("预警刹车文件识别已取消")
        self.files.extend(pending)
        return added, skipped

    def remove_file(self, index):
        if 0 <= index < len(self.files):
            del self.files[index]

    def clear(self):
        self.files.clear()

    def get_files(self):
        return list(self.files)

    def get_total_file_count(self):
        return len(self.files)

    def get_type_file_counts(self):
        counts = {brake_type: 0 for brake_type in self.BRAKE_TYPES}
        for item in self.files:
            brake_type = item.get("预警刹车类型")
            if brake_type in counts:
                counts[brake_type] += 1
        return counts

    def _detect_header_row(self, file_path, sheet_name):
        preview = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=10)
        for row_index in range(len(preview)):
            values = {
                str(value).strip()
                for value in preview.iloc[row_index].dropna().tolist()
            }
            if "编号" in values or "约谈编号" in values:
                return row_index
        raise ValueError("前10行中未找到“编号”或“约谈编号”表头")

    def _detect_type(self, file_path, sheet_name, columns, preview_df):
        columns = {str(column).strip() for column in columns}
        sheet_text = str(sheet_name).strip()
        file_text = os.path.basename(file_path)

        if "约谈编号" in columns or "约谈主题" in columns:
            return "管理约谈"
        if "停工开始时间" in columns or "停工类型" in columns:
            return "停工令"
        if "督办人" in columns or "挂牌督办" in sheet_text or "挂牌督办" in file_text:
            return "挂牌督办"
        if "通报批评" in sheet_text or "通报批评" in file_text:
            return "通报批评"
        if "整改通知" in sheet_text or "整改单" in file_text or "整改通知" in file_text:
            return "整改通知"

        id_column = "编号" if "编号" in preview_df.columns else None
        if id_column:
            ids = preview_df[id_column].dropna().astype(str).str.strip()
            if not ids.empty:
                first_id = ids.iloc[0].upper()
                if first_id.startswith("LFPP"):
                    return "通报批评"
                if first_id.startswith("LFZG"):
                    return "整改通知"
                if first_id.startswith("LFTG"):
                    return "停工令"

        raise ValueError("无法自动识别预警刹车类型")

    def inspect_file(self, file_path):
        workbook = pd.ExcelFile(file_path)
        if not workbook.sheet_names:
            raise ValueError("工作簿中没有可读取的Sheet")

        sheet_name = workbook.sheet_names[0]
        header_row = self._detect_header_row(file_path, sheet_name)
        preview_df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row, nrows=5)
        preview_df.columns = preview_df.columns.astype(str).str.strip()
        brake_type = self._detect_type(file_path, sheet_name, preview_df.columns, preview_df)

        return {
            "sheet_name": sheet_name,
            "header_row": header_row,
            "预警刹车类型": brake_type
        }

    def _normalize_columns(self, df, brake_type=None):
        df = df.copy()
        df.columns = df.columns.astype(str).str.strip()
        rename_map = {}
        for standard_name, aliases in self.FIELD_ALIASES.items():
            for alias in aliases:
                if alias in df.columns:
                    rename_map[alias] = standard_name
                    break
        df = df.rename(columns=rename_map)

        if brake_type is not None:
            source_field = self.UNIT_FIELD_BY_TYPE.get(brake_type)
            if not source_field:
                raise ValueError(f"未配置“{brake_type}”的单位来源字段")
            if source_field not in df.columns:
                raise ValueError(
                    f"预警刹车类型“{brake_type}”缺少单位字段“{source_field}”"
                )
            # All downstream services continue to consume one stable column.
            df["责任单位"] = df[source_field]
            if brake_type == "管理约谈":
                df["责任单位"] = df["责任单位"].apply(
                    self._management_unit_group
                )

            date_candidates = self.DATE_FIELDS_BY_TYPE.get(brake_type, [])
            date_field = next(
                (column for column in date_candidates if column in df.columns), None
            )
            if date_field is None:
                expected = "、".join(date_candidates)
                raise ValueError(
                    f"预警刹车类型“{brake_type}”缺少时间字段（应为：{expected}）"
                )
            df["发出日期"] = df[date_field]

        return df

    @staticmethod
    def _management_unit_group(value):
        """Collapse a detailed interview target into its top-level unit."""
        if pd.isna(value):
            return value
        text = str(value).strip()
        if not text:
            return text
        return re.split(r"[/／（(]", text, maxsplit=1)[0].strip()

    def read_file(self, item):
        metadata = item.get("metadata") or self.inspect_file(item["path"])
        df = pd.read_excel(
            item["path"],
            sheet_name=metadata["sheet_name"],
            header=metadata["header_row"]
        )
        df = self._normalize_columns(
            df, metadata["预警刹车类型"]
        ).dropna(how="all").copy()

        if "预警编号" not in df.columns:
            raise ValueError("未找到可用的预警编号字段")

        df = df[df["预警编号"].notna()].copy()
        df["预警编号"] = df["预警编号"].astype(str).str.strip()
        df = df[df["预警编号"].ne("")].copy()
        df["预警刹车类型"] = metadata["预警刹车类型"]
        df["文件名"] = item["name"]

        # 时间周期由数据中的发出时间决定，不再使用上传顺序。
        if "发出日期" in df.columns:
            parsed_date = pd.to_datetime(df["发出日期"], errors="coerce")
            df["时间周期"] = parsed_date.dt.strftime("%Y-%m")
        else:
            df["时间周期"] = None

        return df

    def load(self, progress_callback=None, cancel_event=None):
        if not self.files:
            return pd.DataFrame(), []

        failed = [item for item in self.files if item["status"] == "识别失败"]
        if failed:
            details = "\n".join(
                f"{item['name']}：{item.get('error', '识别失败')}"
                for item in failed
            )
            raise ValueError("存在无法识别的文件：\n" + details)

        data_list = []
        total = len(self.files)
        for index, item in enumerate(self.files, start=1):
            if cancel_event is not None and cancel_event.is_set():
                raise TaskCancelled("预警刹车数据加载已取消")
            try:
                df = self.read_file(item)
                item["预警刹车类型"] = df["预警刹车类型"].iloc[0] if not df.empty else item["预警刹车类型"]
                item["status"] = "已加载"
                item["rows"] = len(df)
                data_list.append(df)
            except Exception as exc:
                item["status"] = "加载失败"
                item["rows"] = 0
                raise ValueError(f"文件加载失败：{item['name']}\n{exc}") from exc

            if progress_callback:
                progress_callback(index, total, item)
            if cancel_event is not None and cancel_event.is_set():
                raise TaskCancelled("预警刹车数据加载已取消")

        return pd.concat(data_list, ignore_index=True), data_list
