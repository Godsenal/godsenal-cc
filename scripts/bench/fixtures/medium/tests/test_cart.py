import unittest

from src.cart import cart_total


class CartTest(unittest.TestCase):
    def test_single_items(self):
        self.assertEqual(cart_total([{"price": 3, "qty": 1}, {"price": 4, "qty": 1}]), 7)


if __name__ == "__main__":
    unittest.main()
