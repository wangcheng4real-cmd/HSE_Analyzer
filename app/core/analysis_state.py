from dataclasses import dataclass, field


@dataclass
class AnalysisState:
    """单个业务模块的数据加载状态。"""

    df_all: object = None
    df_list: list = field(default_factory=list)
    period_type: str = "week"
    invalid_row_count: int = 0
    loaded: bool = False
    revision: int = 0
    _cache: dict = field(default_factory=dict, repr=False)

    def set_loaded(self, df_all, df_list, invalid_row_count=0):
        self.df_all = df_all
        self.df_list = list(df_list)
        self.invalid_row_count = int(invalid_row_count)
        self.loaded = True
        self.revision += 1
        self.invalidate_cache()

    def invalidate(self):
        self.df_all = None
        self.df_list = []
        self.invalid_row_count = 0
        self.loaded = False
        self.revision += 1
        self.invalidate_cache()

    def clear(self):
        self.invalidate()
        self.period_type = "week"

    def cache_get(self, operation, *args):
        key = (self.revision, self.period_type, operation, args)
        return self._cache.get(key)

    def cache_set(self, operation, value, *args):
        key = (self.revision, self.period_type, operation, args)
        self._cache[key] = value
        return value

    def invalidate_cache(self):
        self._cache.clear()

    @property
    def row_count(self):
        return len(self.df_all) if self.df_all is not None else 0
