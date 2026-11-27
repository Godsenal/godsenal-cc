LIMITS = {"badge": 10, "badge_max": 131}


def count_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
