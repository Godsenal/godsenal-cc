import sys
from collections import defaultdict

from src.pos.sales_reader import read_sales


def by_item(rows):
    totals = defaultdict(int)
    for row in rows:
        totals[row["item"]] += row["amount"]
    return dict(totals)


if __name__ == "__main__":
    for item, total in sorted(by_item(read_sales(sys.argv[2], sys.argv[1])).items()):
        print(f"{item}\t{total}")
