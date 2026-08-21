class CategoryService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    # =========================
    # 大类分析
    # =========================
    def run_main_category(self, df):

        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_category)
        df["大类"] = df[self.cfg.col_category].str.split("/").str[0].str.strip()

        return df["大类"].value_counts()

    # =========================
    # ⭐细类分析（Top10 + 二级分类）
    # =========================
    def run_sub_category(self, df, top_n=10, main_category=None):

        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.with_second_category(df)

        # 2️⃣ 大类过滤
        if main_category:
            df = df[df[self.cfg.col_category].str.startswith(main_category)].copy()
        df["二级分类"] = df[self.preprocessor.SECOND_CATEGORY_COL]

        # 6️⃣ 统计 + Top10
        result = df["二级分类"].value_counts().head(top_n)

        return result
