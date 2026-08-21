import threading
import time
import unittest

import pandas as pd

from app.core.analysis_state import AnalysisState
from app.core.background_task import BackgroundTaskRunner
from app.core.hazard.hazard_data_loader import HazardDataLoader


class FakeRoot:
    def __init__(self):
        self.callbacks = []

    def after(self, _delay, callback):
        self.callbacks.append(callback)

    def poll_once(self):
        callback = self.callbacks.pop(0)
        callback()


class BackgroundTaskTests(unittest.TestCase):
    def test_one_task_only_and_callback_returns_to_caller_thread(self):
        root = FakeRoot()
        main_thread = threading.get_ident()
        seen = {}
        runner = BackgroundTaskRunner(root)

        def worker(_report, _cancel):
            seen["worker"] = threading.get_ident()
            return 42

        self.assertTrue(runner.submit(
            "test", worker,
            lambda value: seen.update(result=value, callback=threading.get_ident()),
            lambda *_args: None
        ))
        self.assertFalse(runner.submit("duplicate", worker, lambda _v: None, lambda *_a: None))
        deadline = time.time() + 2
        while "result" not in seen and time.time() < deadline:
            time.sleep(0.01)
            root.poll_once()
        runner.shutdown()
        self.assertEqual(seen["result"], 42)
        self.assertNotEqual(seen["worker"], main_thread)
        self.assertEqual(seen["callback"], main_thread)


class AnalysisCacheTests(unittest.TestCase):
    def test_cache_is_invalidated_by_data_or_period_change(self):
        state = AnalysisState(period_type="week")
        state.set_loaded(pd.DataFrame({"x": [1]}), [])
        state.cache_set("total", 10)
        self.assertEqual(state.cache_get("total"), 10)

        state.period_type = "month"
        self.assertIsNone(state.cache_get("total"))
        state.cache_set("total", 20)
        state.invalidate()
        self.assertIsNone(state.cache_get("total"))

    def test_cancelled_loader_does_not_replace_invalid_count(self):
        loader = HazardDataLoader()
        loader.files = [{"path": "unused.xlsx", "name": "unused.xlsx"}]
        loader.invalid_date_count = 7
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaisesRegex(Exception, "取消"):
            loader.load(cancel_event=cancelled)
        self.assertEqual(loader.invalid_date_count, 7)


if __name__ == "__main__":
    unittest.main()
