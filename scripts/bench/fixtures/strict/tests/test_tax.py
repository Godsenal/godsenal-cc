import unittest

from src.billing.tax import vat


class Tax(unittest.TestCase):
    def test_round_number(self):
        self.assertEqual(vat(1000), 100)
