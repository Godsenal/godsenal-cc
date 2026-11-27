from datetime import timedelta

from src.core.timeparse import now_utc, parse_ts

STALE_AFTER = timedelta(hours=48)


def is_stale(order, now=None):
    """True when an unshipped order was placed more than 48 hours ago."""
    now = now or now_utc()
    return not order.get("shipped") and now - parse_ts(order["ts"]) > STALE_AFTER
