class UnitABService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor


    # =========================
    # 获取单位列表
    # =========================
    def get_units(self, df):

        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_level)

        # 只统计AB类隐患
        df = df[
            df[self.cfg.col_level]
            .astype(str)
            .str.strip()
            .str.upper()
            .isin([
                "A",
                "B",
                "A级",
                "B级"
            ])
        ].copy()

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
    # 单位AB类隐患TOP3
    # =========================
    def unit_ab_top3(self, df, unit):


        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_unit)


        # 2.单位过滤

        df = df[df[self.cfg.col_unit].eq(unit)].copy()


        # 3.AB级过滤

        df = df[
            df[self.cfg.col_level]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "A",
                    "B",
                    "A级",
                    "B级"
                ]
            )
        ]


        if len(df)==0:
            return {}



        # 4.隐患分类第二级

        df = self.preprocessor.with_category_path2(df)
        df["AB类别"] = df[self.preprocessor.CATEGORY_PATH2_COL].apply(
            lambda value: value.split("/")[1] if "/" in value else value
        )



        # 5.TOP3

        result = (
            df["AB类别"]
            .value_counts()
            .sort_values(
                ascending=False
            )
            .head(3)
        )


        return result
