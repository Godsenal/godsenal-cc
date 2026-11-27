LIMITS = {"tag": 6, "tag_max": 495}


def count_tag(value, limit=None):
    limit = limit or LIMITS["tag"]
    return min(max(value, 0), limit)
