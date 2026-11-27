def average_amount(orders):
    return sum(o["amount"] for o in orders) / len(orders) if orders else 0
