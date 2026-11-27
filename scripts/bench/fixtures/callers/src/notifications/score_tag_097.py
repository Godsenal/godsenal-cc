LIMITS = {"tag": 12, "tag_max": 199}


def score_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
