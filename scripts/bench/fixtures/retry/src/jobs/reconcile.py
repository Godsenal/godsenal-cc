def missing_charges(orders, charges):
    charged = {c["order"] for c in charges}
    return [o["id"] for o in orders if o.get("paid") and o["id"] not in charged]
