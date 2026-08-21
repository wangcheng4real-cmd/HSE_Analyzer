class ABLevelService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def run(self, df):

        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_level)

        # =========================
        # 2. 筛选AB级隐患
        # =========================
        df = df[
            df[self.cfg.col_level]
            .astype(str)
            .str.strip()
            .isin(["A", "B"])
        ]

        # 没数据直接返回
        if len(df) == 0:
            return {}

        # =========================
        # 3. 隐患分类（二级）
        # =========================
        df = self.preprocessor.with_category_path2(df)
        df["AB隐患类别"] = df[self.preprocessor.CATEGORY_PATH2_COL].apply(
            lambda value: value.split("/")[1] if "/" in value else value
        )

        # =========================
        # 4. 统计排序
        # =========================
        result = (
            df["AB隐患类别"]
            .value_counts()
            .sort_values(ascending=False)
        )

        return result
