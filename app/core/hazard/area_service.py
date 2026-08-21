class AreaService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def run(self, df):

        df = self.preprocessor.filter_contractor_flow(df)
        df = self.preprocessor.with_main_area(df)
        result = df[self.preprocessor.MAIN_AREA_COL].value_counts()

        return result
