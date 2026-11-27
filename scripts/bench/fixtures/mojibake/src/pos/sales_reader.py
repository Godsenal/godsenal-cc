import csv
import io


def read_sales(path, store):
    """Sales rows of a store's POS export: [{"item": str, "qty": int, "amount": int}]."""
    with open(path, "rb") as f:
        text = f.read().decode("utf-8", errors="replace")
    return [{"item": r["item"], "qty": int(r["qty"]), "amount": int(r["amount"])}
            for r in csv.DictReader(io.StringIO(text))]
