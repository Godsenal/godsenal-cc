import csv


def read_stock(path, store):
    """Stock rows of a store's POS export: {sku: (name, qty)}."""
    with open(path, encoding="utf-8", newline="") as f:
        return {r["sku"]: (r["name"], int(r["qty"])) for r in csv.DictReader(f)}
