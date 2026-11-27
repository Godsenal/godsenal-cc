import unittest

from src.money import format_money, format_pct


class Money(unittest.TestCase):
    def test_won(self):
        self.assertEqual(format_money(1234), "1,234원")

    def test_pct(self):
        self.assertEqual(format_pct(2.5), "2.5%")
