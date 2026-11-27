def subtotal(order):
    return sum(item["price"] * item["qty"] for item in order["items"])


def item_lines(order):
    return [(item["name"], item["price"] * item["qty"]) for item in order["items"]]
