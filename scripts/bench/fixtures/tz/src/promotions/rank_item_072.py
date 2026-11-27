def rank_items(items, key="item_id"):
    """Rank items by {key}."""
    out = {}
    for item in items:
        out.setdefault(item.get(key), []).append(item)
    return out
