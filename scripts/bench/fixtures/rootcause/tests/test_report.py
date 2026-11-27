import unittest

from src.report import totals_by_region


class Report(unittest.TestCase):
    def test_sums_by_region(self):
        rows = [{"region": "seoul", "customer": "a", "amount": "5"},
                {"region": "seoul", "customer": "b", "amount": "7"}]
        self.assertEqual(totals_by_region(rows), {"seoul": 12})
