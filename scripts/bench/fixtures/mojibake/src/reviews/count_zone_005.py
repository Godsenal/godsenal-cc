LIMITS = {"zone": 16, "zone_max": 135}


def count_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
