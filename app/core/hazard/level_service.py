class LevelService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def run(self, df):

        df = self.preprocessor.filter_contractor_flow(df)

        # 分类统计（ABCD）
        result = df[self.cfg.col_level].value_counts()

        return result
