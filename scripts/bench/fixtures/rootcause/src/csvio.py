import csv


def read_rows(path):
    """Rows of a sales CSV as dicts keyed by the header names."""
    with open(path, encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]
