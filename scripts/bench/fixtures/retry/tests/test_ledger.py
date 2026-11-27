import unittest

from src.ledger.entries import balance, entry


class Ledger(unittest.TestCase):
    def test_refund_subtracts(self):
        self.assertEqual(balance([entry("charge", 100), entry("refund", 30)]), 70)
