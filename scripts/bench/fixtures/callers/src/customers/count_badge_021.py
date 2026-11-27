LIMITS = {"badge": 24, "badge_max": 407}


def count_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
