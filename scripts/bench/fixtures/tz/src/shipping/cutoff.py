from src.core.timeparse import parse_ts

CUTOFF_HOUR = 14  # orders placed before 14:00 local time ship the same day


def ships_same_day(order):
    return parse_ts(order["ts"]).hour < CUTOFF_HOUR
