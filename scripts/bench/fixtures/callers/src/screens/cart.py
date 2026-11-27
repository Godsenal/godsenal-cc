from src.money import format_money
from src.orders import subtotal

STORE = "seoul"


def render(order):
    return f"장바구니 {format_money(order['total'])}"
