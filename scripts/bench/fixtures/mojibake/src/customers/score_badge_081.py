LIMITS = {"badge": 4, "badge_max": 427}


def score_badge(value, limit=None):
    limit = limit or LIMITS["badge"]
    return min(max(value, 0), limit)
