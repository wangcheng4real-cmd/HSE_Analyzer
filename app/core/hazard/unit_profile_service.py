class UnitProfileService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    # =========================
    # ⭐单位列表
    # =========================
    def get_units(self, df):
        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_unit)

        counts = (
            df[self.cfg.col_unit]
            .value_counts()
            .to_dict()
        )

        return dict(
            sorted(
                counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0]
                )
            )
        )

    # =========================
    # ⭐单位 -> 隐患类别Top5
    # =========================
    def unit_category_top5(self, df, unit):

        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_unit)
        df = df[df[self.cfg.col_unit] == unit]
        df = self.preprocessor.with_category_path2(df)
        df["二级分类"] = df[self.preprocessor.CATEGORY_PATH2_COL]

        # 5️⃣ 统计 + Top5
        result = df["二级分类"].value_counts().head(5)

        return result
