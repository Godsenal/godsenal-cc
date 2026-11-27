LIMITS = {"tag": 38, "tag_max": 383}


def score_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
