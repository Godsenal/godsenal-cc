from collections import defaultdict

from src.core.dates import order_date


def weekly_totals(orders):
    totals = defaultdict(int)
    for order in orders:
        year, week, _ = order_date(order).isocalendar()
        totals[(order["store"], year, week)] += order["amount"]
    return dict(totals)
