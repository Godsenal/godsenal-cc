from src.core.dates import order_date


def invoice(order):
    return {"order": order["id"], "date": order_date(order).isoformat(), "amount": order["amount"]}
