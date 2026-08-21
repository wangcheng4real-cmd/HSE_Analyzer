class AreaABService:

    MAIN_AREA_COL = "区域大类"

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor

    def _prepare_area_df(self, df, ab_only=False):
        df = self.preprocessor.normalize_columns(df)

        required_columns = [
            self.cfg.col_flow,
            self.cfg.col_area
        ]

        if ab_only:
            required_columns.append(self.cfg.col_level)

        if self.preprocessor.require_columns(df, required_columns):
            return df.iloc[0:0].copy()
        df = self.preprocessor.filter_contractor_flow(df)

        if ab_only:
            df = df[
                df[self.cfg.col_level]
                .astype(str)
                .str.strip()
                .str.upper()
                .isin(["A", "B", "A级", "B级"])
            ].copy()

        return self.preprocessor.with_main_area(df)

    # =========================
    # 获取区域及AB类隐患数量
    # =========================
    def get_areas(self, df):
        df = self._prepare_area_df(df, ab_only=True)

        if df.empty:
            return {}

        counts = (
            df[self.MAIN_AREA_COL]
            .value_counts()
            .to_dict()
        )

        return dict(
            sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0])
            )
        )

    # =========================
    # 区域AB隐患类别TOP3
    # =========================
    def area_ab_top3(self, df, area):
        df = self._prepare_area_df(df, ab_only=True)

        if df.empty or self.cfg.col_category not in df.columns:
            return {}

        df = df[df[self.MAIN_AREA_COL].eq(area)].copy()
        df = df[df[self.cfg.col_category].notna()].copy()

        if df.empty:
            return {}

        df = self.preprocessor.with_category_path2(df)
        df["隐患类别二级"] = df[self.preprocessor.CATEGORY_PATH2_COL]

        return (
            df["隐患类别二级"]
            .value_counts()
            .sort_values(ascending=False)
            .head(3)
        )

