import unittest

from src.retry import call_with_retry


class RetryTest(unittest.TestCase):
    def test_returns_value(self):
        self.assertEqual(call_with_retry(lambda: 5), 5)


if __name__ == "__main__":
    unittest.main()
