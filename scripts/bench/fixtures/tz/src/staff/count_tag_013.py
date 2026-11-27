LIMITS = {"tag": 20, "tag_max": 271}


def count_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
