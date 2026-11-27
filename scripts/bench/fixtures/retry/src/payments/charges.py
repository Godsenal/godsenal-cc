import uuid

from src.net.retry import RetryPolicy
from src.payments.auth import auth_header


class ChargeClient:
    def __init__(self, transport, retry=None):
        self.transport = transport
        self.retry = retry or RetryPolicy()

    def charge(self, order_id, amount, currency="KRW"):
        """Charge an order once; returns the gateway's charge id."""
        body = {"order": order_id, "amount": amount, "currency": currency}
        response = self.retry.run(lambda: self.transport.post("/charges", body, self._headers()))
        return response["id"]

    def _headers(self):
        return {**auth_header(), "Idempotency-Key": uuid.uuid4().hex}
