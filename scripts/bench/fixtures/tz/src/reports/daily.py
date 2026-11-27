import sys
from collections import defaultdict

from src.core.dates import order_date
from src.core.io import read_orders


def daily_totals(orders):
    """{(store, date): total} by the order's own date."""
    totals = defaultdict(int)
    for order in orders:
        totals[(order["store"], order_date(order))] += order["amount"]
    return dict(totals)


if __name__ == "__main__":
    for (store, day), total in sorted(daily_totals(read_orders(sys.argv[1])).items()):
        print(f"{store}\t{day}\t{total}")
