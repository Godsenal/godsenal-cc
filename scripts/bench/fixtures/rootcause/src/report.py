import sys
from collections import defaultdict

from src.csvio import read_rows


def totals_by_region(rows):
    totals = defaultdict(int)
    for row in rows:
        totals[row.get("region") or "unknown"] += int(row["amount"])
    return dict(totals)


def main(path):
    for region, total in sorted(totals_by_region(read_rows(path)).items()):
        print(f"{region}\t{total}")


if __name__ == "__main__":
    main(sys.argv[1])
