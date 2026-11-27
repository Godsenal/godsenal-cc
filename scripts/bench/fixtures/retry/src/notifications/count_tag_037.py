LIMITS = {"tag": 32, "tag_max": 179}


def count_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
