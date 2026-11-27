def entry(kind, amount):
    sign = -1 if kind == "refund" else 1
    return {"kind": kind, "amount": sign * amount}


def balance(entries):
    return sum(e["amount"] for e in entries)
