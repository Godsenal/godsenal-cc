import unittest

from src.reports.daily import daily_totals


class Daily(unittest.TestCase):
    def test_sums_same_store_same_day(self):
        orders = [{"store": "nyc", "ts": "2026-03-01T10:00:00-05:00", "amount": 5},
                  {"store": "nyc", "ts": "2026-03-01T12:00:00-05:00", "amount": 7}]
        self.assertEqual(list(daily_totals(orders).values()), [12])
