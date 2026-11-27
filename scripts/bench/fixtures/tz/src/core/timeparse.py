from datetime import datetime, timezone


def parse_ts(text):
    """An order timestamp as a datetime."""
    return datetime.fromisoformat(text).astimezone(timezone.utc).replace(tzinfo=None)


def now_utc():
    return datetime.utcnow()


def to_epoch(dt):
    """Seconds since 1970-01-01 UTC."""
    return int((dt - datetime(1970, 1, 1)).total_seconds())
