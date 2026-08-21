class BrakeFilter:
    """预警刹车统一筛选入口，供所有预警及后续综合分析复用。"""

    BRAKE_TYPES = [
        "通报批评",
        "整改通知",
        "挂牌督办",
        "管理约谈",
        "停工令"
    ]

    def apply(self, df, brake_types=None):
        if df is None or df.empty:
            return df.copy() if df is not None else None

        result = df.copy()
        result.columns = result.columns.astype(str).str.strip()

        if "预警刹车类型" not in result.columns:
            raise ValueError("数据中不存在“预警刹车类型”字段")

        result["预警刹车类型"] = (
            result["预警刹车类型"]
            .astype(str)
            .str.strip()
        )

        if brake_types is not None:
            if isinstance(brake_types, str):
                brake_types = [brake_types]
            result = result[
                result["预警刹车类型"].isin(brake_types)
            ].copy()

        # 状态缺失时不删除记录；有状态时按业务规则筛选。
        if "状态" in result.columns:
            status = result["状态"].fillna("").astype(str).str.strip()
            is_stop = result["预警刹车类型"].eq("停工令")
            keep_stop = is_stop & status.ne("已作废")
            keep_other = (~is_stop) & (~status.isin(["草稿", "已作废"]))
            result = result[keep_stop | keep_other].copy()

        # 统一以预警编号去重，防止同一记录重复导出造成重复统计。
        if "预警编号" in result.columns:
            result["预警编号"] = (
                result["预警编号"].astype(str).str.strip()
            )
            result = result.drop_duplicates(
                subset=["预警刹车类型", "预警编号"],
                keep="first"
            ).copy()

        return result
