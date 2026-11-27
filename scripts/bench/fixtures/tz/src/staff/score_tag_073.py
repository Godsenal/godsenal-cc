LIMITS = {"tag": 50, "tag_max": 291}


def score_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
