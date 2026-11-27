LIMITS = {"badge": 42, "badge_max": 519}


def score_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
