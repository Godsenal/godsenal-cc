from collections import Counter

from src.core.dates import order_hour


def orders_by_hour(orders):
    return dict(Counter(order_hour(order) for order in orders))
