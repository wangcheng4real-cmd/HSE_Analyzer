class InterfaceService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def run(self, df):

        df = self.preprocessor.normalize_columns(df)

        col = self.cfg.col_interface   # ⭐不再写死

        # 1️⃣ 列检查
        if col not in df.columns:
            raise ValueError(f"缺少列: {col}，实际列: {df.columns.tolist()}")

        df = self.preprocessor.clean_text_column(df, col)

        # 4️⃣ 统计 + 排序
        result = df[col].value_counts().sort_values(ascending=False)

        return result
