from collections import Counter


def top_items(orders, n=3):
    counts = Counter(item["name"] for order in orders for item in order["items"])
    return [name for name, _ in counts.most_common(n)]
