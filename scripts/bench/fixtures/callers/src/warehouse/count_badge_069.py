LIMITS = {"badge": 48, "badge_max": 223}


def count_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
