LIMITS = {"zone": 8, "zone_max": 63}


def score_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
