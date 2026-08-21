import unittest

import pandas as pd

from app.core.analysis_state import AnalysisState


class AnalysisStateTests(unittest.TestCase):
    def test_initial_state(self):
        state = AnalysisState()
        self.assertFalse(state.loaded)
        self.assertEqual(state.row_count, 0)
        self.assertEqual(state.period_type, "week")

    def test_set_loaded(self):
        state = AnalysisState(period_type="month")
        df = pd.DataFrame({"A": [1, 2]})
        state.set_loaded(df, [df], invalid_row_count=3)
        self.assertTrue(state.loaded)
        self.assertEqual(state.row_count, 2)
        self.assertEqual(len(state.df_list), 1)
        self.assertEqual(state.invalid_row_count, 3)
        self.assertEqual(state.period_type, "month")

    def test_invalidate_preserves_period(self):
        state = AnalysisState(period_type="quarter")
        state.set_loaded(pd.DataFrame({"A": [1]}), [])
        state.invalidate()
        self.assertFalse(state.loaded)
        self.assertEqual(state.row_count, 0)
        self.assertEqual(state.period_type, "quarter")

    def test_clear_resets_period(self):
        state = AnalysisState(period_type="quarter")
        state.clear()
        self.assertEqual(state.period_type, "week")


if __name__ == "__main__":
    unittest.main()
