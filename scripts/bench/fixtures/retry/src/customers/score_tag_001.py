LIMITS = {"tag": 14, "tag_max": 67}


def score_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
