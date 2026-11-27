from src.net.retry import RetryPolicy
from src.payments.auth import signed_headers


def payout(transport, store, amount, retry=None):
    """Pay a store its balance once; returns the gateway's payout id."""
    body = {"store": store, "amount": amount}
    return (retry or RetryPolicy()).run(lambda: transport.post("/payouts", body, signed_headers()))["id"]
