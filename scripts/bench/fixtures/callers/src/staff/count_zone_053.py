LIMITS = {"zone": 40, "zone_max": 451}


def count_zone(value, limit=None):
    limit = limit or LIMITS["zone"]
    return min(max(value, 0), limit)
