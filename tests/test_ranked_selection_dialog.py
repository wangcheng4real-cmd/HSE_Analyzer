import unittest

from app.ui.components.ranked_selection_dialog import (
    sort_ranked_items,
    filter_ranked_items,
)


class RankedSelectionLogicTests(unittest.TestCase):
    def test_sorts_by_count_then_name(self):
        result = sort_ranked_items({"单位乙": 5, "单位甲": 5, "单位丙": 9})
        self.assertEqual(result, [("单位丙", 9), ("单位乙", 5), ("单位甲", 5)])

    def test_filters_by_name_without_changing_order(self):
        items = [("5号核岛", 20), ("控制区内BOP设施", 10), ("控制区外BOP设施", 8)]
        self.assertEqual(
            filter_ranked_items(items, "BOP"),
            [("控制区内BOP设施", 10), ("控制区外BOP设施", 8)]
        )

    def test_empty_query_returns_all_items(self):
        items = [("单位甲", 2), ("单位乙", 1)]
        self.assertEqual(filter_ranked_items(items, "  "), items)


if __name__ == "__main__":
    unittest.main()
