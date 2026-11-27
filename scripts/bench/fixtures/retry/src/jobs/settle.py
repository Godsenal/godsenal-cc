from src.payments.charges import ChargeClient


def settle_all(transport, orders):
    client = ChargeClient(transport)
    return {order["id"]: client.charge(order["id"], order["amount"]) for order in orders if not order.get("paid")}
