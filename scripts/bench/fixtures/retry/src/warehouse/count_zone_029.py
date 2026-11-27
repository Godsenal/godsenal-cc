LIMITS = {"zone": 28, "zone_max": 543}


def count_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
