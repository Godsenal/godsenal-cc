import csv
from pathlib import Path


def import_members(path, store):
    """Members of a store's POS export: [{"id": str, "name": str}]."""
    lines = Path(path).read_text().splitlines()
    return [{"id": r["id"], "name": r["name"]} for r in csv.DictReader(lines)]
