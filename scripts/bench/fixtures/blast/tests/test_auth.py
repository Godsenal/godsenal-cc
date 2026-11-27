import os
import tempfile
import unittest

from src.auth import login, signup
from src.store import Store


class Auth(unittest.TestCase):
    def test_signup_then_login(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d, "users.json"))
            signup(store, "carol@example.com", "pw")
            self.assertTrue(login(store, "carol@example.com", "pw"))
            self.assertFalse(login(store, "carol@example.com", "nope"))
