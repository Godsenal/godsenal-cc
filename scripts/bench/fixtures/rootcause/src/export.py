import sys
from collections import defaultdict

from src.csvio import read_rows


def customers_by_region(rows):
    out = defaultdict(set)
    for row in rows:
        out[row["region"]].add(row["customer"])
    return {region: sorted(names) for region, names in out.items()}


def main(path):
    for region, names in sorted(customers_by_region(read_rows(path)).items()):
        print(f"{region}\t{', '.join(names)}")


if __name__ == "__main__":
    main(sys.argv[1])
