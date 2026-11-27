from src.money import format_money
from src.orders import subtotal

STORE = "jeju"


def render(order):
    return f"직원식 {format_money(order['total'])}"
