class UnitService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def run(self, df):

        df = self.preprocessor.filter_contractor_flow(df)

        # 单位统计 + 排序
        result = (
            df.groupby(self.cfg.col_unit)[self.cfg.col_id]
            .count()
            .sort_values(ascending=False)
        )

        return result
