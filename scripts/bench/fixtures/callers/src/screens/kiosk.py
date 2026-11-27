from src.money import format_money as fmt

STORE = "tokyo"


def render(order):
    return f"키오스크 {fmt(order['total'])} (할인 {fmt(order['discount'])})"
