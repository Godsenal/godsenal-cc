from src.money import format_money
from src.orders import subtotal

STORE = "nyc"


def render(order):
    return f"배달 {format_money(order['total'])}"
