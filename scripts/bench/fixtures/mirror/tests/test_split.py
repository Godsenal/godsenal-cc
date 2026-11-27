import unittest

from src.split import split_bill


class Split(unittest.TestCase):
    def test_even(self):
        self.assertEqual(split_bill(100, 4), [25, 25, 25, 25])

    def test_three_ways(self):
        self.assertEqual(split_bill(100, 3), [33, 33, 33])
