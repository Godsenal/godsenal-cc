import unittest

from src.reports.sales import by_item


class Sales(unittest.TestCase):
    def test_by_item(self):
        rows = [{"item": "a", "qty": 1, "amount": 5}, {"item": "a", "qty": 1, "amount": 7}]
        self.assertEqual(by_item(rows), {"a": 12})
