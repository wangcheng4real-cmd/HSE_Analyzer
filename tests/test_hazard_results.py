import unittest

import pandas as pd

from app.core.hazard.results import TrendPoint, TrendSeries, MultiSeriesTrend


class HazardResultTests(unittest.TestCase):
    def test_trend_series_properties_and_legacy_conversion(self):
        point = TrendPoint("2026年01月", pd.Timestamp("2026-01-01"), 5)
        result = TrendSeries([point])
        self.assertFalse(result.empty)
        self.assertEqual(result.periods, ["2026年01月"])
        self.assertEqual(result.counts, [5])
        self.assertEqual(result.to_legacy()[0]["数量"], 5)

    def test_empty_trend_series(self):
        self.assertTrue(TrendSeries().empty)
        self.assertEqual(TrendSeries().to_legacy(), [])

    def test_multi_series_and_legacy_conversion(self):
        result = MultiSeriesTrend(
            periods=["第一周"],
            series={"单位甲": [2]},
            totals={"单位甲": 2}
        )
        self.assertFalse(result.empty)
        legacy = result.to_legacy()
        self.assertEqual(legacy["series"]["单位甲"], [2])


if __name__ == "__main__":
    unittest.main()
