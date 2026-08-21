import unittest

import pandas as pd

from app.core.hazard.hazard_data_loader import HazardDataLoader


class PeriodGroupingTests(unittest.TestCase):
    def setUp(self):
        self.loader = HazardDataLoader()
        self.raw = pd.DataFrame({
            "检查日期": pd.to_datetime([
                "2024-02-29", "2025-12-29", "2026-01-04", "2026-01-05",
                "2026-03-31", "2026-04-01", "2026-06-30", "2026-07-01",
                "2026-09-30", "2026-10-01"
            ])
        })

    def labels(self, mode):
        _, groups = self.loader.group_by_period(self.raw, mode)
        return [group["时间周期"].iloc[0] for group in groups]

    def test_week_boundaries(self):
        labels = self.labels("week")
        self.assertIn("2025-12-29 至 2026-01-04", labels)
        self.assertIn("2026-03-30 至 2026-04-05", labels)

    def test_month_and_leap_day(self):
        self.assertIn("2024年02月", self.labels("month"))

    def test_natural_quarters(self):
        labels = self.labels("quarter")
        for label in ("2026年第1季度", "2026年第2季度", "2026年第3季度", "2026年第4季度"):
            self.assertIn(label, labels)

    def test_switching_preserves_rows(self):
        for mode in ("week", "month", "quarter"):
            grouped, _ = self.loader.group_by_period(self.raw, mode)
            self.assertEqual(len(grouped), len(self.raw))

    def test_rejects_unknown_period(self):
        with self.assertRaises(ValueError):
            self.loader.group_by_period(self.raw, "year")


if __name__ == "__main__":
    unittest.main()
