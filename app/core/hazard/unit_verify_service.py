class UnitVerifyService:

    def __init__(self, cfg, preprocessor):
        self.cfg = cfg
        self.preprocessor = preprocessor


    def run(self, df):

        df = self.preprocessor.normalize_columns(df)


        unit_col = self.cfg.col_unit
        verify_col = self.cfg.col_verify


        # ======================
        # 1.过滤空单位
        # ======================

        df = self.preprocessor.clean_text_column(df, unit_col)


        # ======================
        # 2.单位统计
        # ======================

        result = {}


        for unit, group in df.groupby(unit_col):


            total = len(group)


            if total == 0:
                continue



            # 已按期验证 + 按期验证中

            ok_count = group[
                group[verify_col]
                .astype(str)
                .str.strip()
                .isin(
                    [
                        "已按期验证",
                        "按期验证中"
                    ]
                )
            ].shape[0]


            rate = ok_count / total


            result[unit] = rate



        # ======================
        # 3.从低到高排序
        # ======================

        result = sorted(
            result.items(),
            key=lambda x:x[1]
        )


        return result
