LIMITS = {"badge": 36, "badge_max": 315}


def count_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
