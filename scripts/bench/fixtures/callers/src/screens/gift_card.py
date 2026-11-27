from src.money import format_money
from src.orders import subtotal

STORE = "tokyo"


def render(order):
    return f"기프트카드 {format_money(order['total'])}"
