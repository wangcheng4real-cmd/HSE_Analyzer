class HazardPreprocessor:
    CONTRACTOR_FLOW = "工程公司录入承包商"
    MAIN_AREA_COL = "区域大类"
    CATEGORY_PATH2_COL = "隐患类别二级路径"
    SECOND_CATEGORY_COL = "隐患第二级分类"

    def __init__(self, cfg):
        self.cfg = cfg
        self.CONTRACTOR_FLOW = cfg.contractor_flow
        self.MAIN_AREA_COL = cfg.col_main_area
        self.CATEGORY_PATH2_COL = cfg.col_category_path2
        self.SECOND_CATEGORY_COL = cfg.col_second_category

    def normalize_columns(self, df):
        result = df.copy()
        result.columns = result.columns.astype(str).str.strip()
        return result

    def require_columns(self, df, columns):
        return [column for column in columns if column not in df.columns]

    def clean_text_column(self, df, column):
        result = self.normalize_columns(df)
        if column not in result.columns:
            return result.iloc[0:0].copy()
        result = result[result[column].notna()].copy()
        result[column] = result[column].astype(str).str.strip()
        return result[result[column].ne("")].copy()

    def filter_contractor_flow(self, df):
        result = self.clean_text_column(df, self.cfg.col_flow)
        if result.empty:
            return result
        return result[result[self.cfg.col_flow].eq(self.CONTRACTOR_FLOW)].copy()

    def with_main_area(self, df):
        result = self.clean_text_column(df, self.cfg.col_area)
        if result.empty:
            result[self.MAIN_AREA_COL] = None
            return result
        result[self.MAIN_AREA_COL] = (
            result[self.cfg.col_area].str.split("/").str[0].str.strip()
        )
        return result[result[self.MAIN_AREA_COL].ne("")].copy()

    def with_category_path2(self, df):
        result = self.clean_text_column(df, self.cfg.col_category)
        if result.empty:
            result[self.CATEGORY_PATH2_COL] = None
            return result
        result[self.CATEGORY_PATH2_COL] = result[self.cfg.col_category].apply(
            lambda value: "/".join(str(value).strip().split("/")[:2])
        )
        return result[result[self.CATEGORY_PATH2_COL].ne("")].copy()

    def with_second_category(self, df):
        result = self.clean_text_column(df, self.cfg.col_category)
        if result.empty:
            result[self.SECOND_CATEGORY_COL] = None
            return result
        parts = result[self.cfg.col_category].str.split("/")
        result = result[parts.str.len().ge(2)].copy()
        result[self.SECOND_CATEGORY_COL] = (
            result[self.cfg.col_category].str.split("/").str[1].str.strip()
        )
        return result[result[self.SECOND_CATEGORY_COL].ne("")].copy()
