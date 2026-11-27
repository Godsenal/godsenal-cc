import unittest

from src.catalog.sku import normalize_sku


class Sku(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_sku(" cold brew "), "COLD-BREW")
