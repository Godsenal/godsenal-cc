from src.core.timeparse import parse_ts


def in_event_order(orders):
    """Orders of every store, earliest first (the order they actually happened in)."""
    return sorted(orders, key=lambda o: parse_ts(o["ts"]))
