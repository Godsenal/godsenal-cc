LIMITS = {"tag": 44, "tag_max": 87}


def count_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
