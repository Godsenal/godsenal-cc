LIMITS = {"zone": 2, "zone_max": 359}


def count_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
