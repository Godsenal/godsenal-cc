import uuid

from src.net.retry import RetryPolicy
from src.payments.auth import auth_header


def refund(transport, charge_id, amount, retry=None):
    """Refund part or all of a charge once; returns the gateway's refund id."""
    retry = retry or RetryPolicy()

    def send():
        headers = {**auth_header(), "Idempotency-Key": str(uuid.uuid4())}
        return transport.post("/refunds", {"charge": charge_id, "amount": amount}, headers)

    return retry.run(send)["id"]
