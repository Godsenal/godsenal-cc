LIMITS = {"tag": 26, "tag_max": 475}


def score_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
