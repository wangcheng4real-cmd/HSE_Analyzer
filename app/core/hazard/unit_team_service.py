class UnitTeamService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor


    # =========================
    # 获取单位列表
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
    # 单位责任班组TOP5
    # =========================
    def unit_team_top5(self, df, unit):


        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.clean_text_column(df, self.cfg.col_unit)


        # 2.单位过滤

        df = df[df[self.cfg.col_unit].eq(unit)].copy()


        # 3.责任班组过滤

        col_team = self.cfg.col_team


        if col_team not in df.columns:
            raise ValueError(
                "Excel不存在责任班组字段"
            )


        df = self.preprocessor.clean_text_column(df, col_team)


        # 4.统计TOP5

        result = (
            df[col_team]
            .value_counts()
            .sort_values(
                ascending=False
            )
            .head(5)
        )


        return result
