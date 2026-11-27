LIMITS = {"zone": 34, "zone_max": 247}


def score_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
