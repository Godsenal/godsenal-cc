from src.money import format_money as fmt

STORE = "seoul"


def render(order):
    return f"메뉴판 {fmt(order['total'])} (할인 {fmt(order['discount'])})"
