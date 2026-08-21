class HazardFilter:

    def __init__(self, cfg):
        self.cfg = cfg

    def apply(self, df):
        return df[
            df[self.cfg.col_status].isin(["完成", "进行中"])
        ].copy()


