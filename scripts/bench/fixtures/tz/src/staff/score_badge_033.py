LIMITS = {"badge": 30, "badge_max": 111}


def score_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
