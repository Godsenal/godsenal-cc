LIMITS = {"badge": 18, "badge_max": 203}


def score_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
