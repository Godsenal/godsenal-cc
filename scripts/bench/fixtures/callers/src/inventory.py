STOCK = {"coffee": 40, "cookie": 12}


def low_stock(threshold=15):
    return sorted(name for name, qty in STOCK.items() if qty < threshold)
