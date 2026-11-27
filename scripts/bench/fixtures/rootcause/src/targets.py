import csv
import sys


def read_targets(path):
    """Monthly sales target per region, from the targets sheet: {region: amount}."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    region, amount = header.index("region"), header.index("target")
    return {row[region]: int(row[amount]) for row in body}


if __name__ == "__main__":
    for region, target in sorted(read_targets(sys.argv[1]).items()):
        print(f"{region}\t{target}")
