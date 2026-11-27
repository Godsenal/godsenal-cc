RATES = {"seoul": 10, "nyc": 8, "tokyo": 10}


def tax(order):
    return order["amount"] * RATES.get(order["store"], 0) // 100
