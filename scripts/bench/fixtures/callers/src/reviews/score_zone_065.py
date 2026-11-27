LIMITS = {"zone": 46, "zone_max": 155}


def score_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
