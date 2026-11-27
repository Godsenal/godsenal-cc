LIMITS = {"zone": 22, "zone_max": 339}


def score_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
