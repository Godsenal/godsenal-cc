from src.core.timeparse import parse_ts, to_epoch


def cursor_after(orders):
    """The sync cursor after a batch: the epoch second of its latest order (the gateway resumes from there)."""
    return max(to_epoch(parse_ts(o["ts"])) for o in orders)
