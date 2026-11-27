from src.money import format_money as fmt

STORE = "busan"


def render(order):
    return f"사전주문 {fmt(order['total'])} (할인 {fmt(order['discount'])})"
