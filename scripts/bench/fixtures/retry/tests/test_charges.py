import unittest

from tests.fake_gateway import FakeGateway

from src.net.retry import RetryPolicy
from src.payments.charges import ChargeClient


class Charges(unittest.TestCase):
    def test_charge_returns_the_gateway_id(self):
        gw = FakeGateway()
        client = ChargeClient(gw, RetryPolicy(sleep=lambda s: None))
        self.assertEqual(client.charge("o1", 1000), "charges_1")
        self.assertEqual(len(gw.processed), 1)
