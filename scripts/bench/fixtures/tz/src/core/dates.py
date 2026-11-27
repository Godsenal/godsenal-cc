from src.core.timeparse import parse_ts


def order_date(order):
    """The date an order belongs to."""
    return parse_ts(order["ts"]).date()


def order_hour(order):
    return parse_ts(order["ts"]).hour
