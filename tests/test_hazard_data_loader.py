import os
import tempfile
import unittest

import pandas as pd

from app.core.hazard.hazard_data_loader import HazardDataLoader


class HazardDataLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.loader = HazardDataLoader()

    def tearDown(self):
        self.tempdir.cleanup()

    def write_excel(self, name, data):
        path = os.path.join(self.tempdir.name, name)
        pd.DataFrame(data).to_excel(path, index=False)
        return path

    def test_duplicate_file_is_skipped(self):
        path = self.write_excel("one.xlsx", {"检查日期": ["2026-01-05"]})
        added, skipped = self.loader.add_files([path, path])
        self.assertEqual(added, 1)
        self.assertEqual(skipped, ["one.xlsx"])

    def test_missing_date_column_raises(self):
        path = self.write_excel("bad.xlsx", {"其他字段": [1]})
        self.loader.add_files([path])
        with self.assertRaisesRegex(ValueError, "检查日期"):
            self.loader.load()

    def test_invalid_dates_are_excluded(self):
        path = self.write_excel("dates.xlsx", {"检查日期": ["2026-01-05", "bad", None]})
        self.loader.add_files([path])
        df_all, _ = self.loader.load()
        self.assertEqual(len(df_all), 1)
        # Excel尾部全空行不会被read_excel载入，只有"bad"参与无效计数。
        self.assertEqual(self.loader.invalid_date_count, 1)

    def test_files_in_same_week_are_merged(self):
        first = self.write_excel("a.xlsx", {"检查日期": ["2026-01-05"]})
        second = self.write_excel("b.xlsx", {"检查日期": ["2026-01-11"]})
        self.loader.add_files([first, second])
        df_all, groups = self.loader.load(period_type="week")
        self.assertEqual(len(df_all), 2)
        self.assertEqual(len(groups), 1)
        self.assertEqual(set(df_all["文件名"]), {"a.xlsx", "b.xlsx"})


if __name__ == "__main__":
    unittest.main()
