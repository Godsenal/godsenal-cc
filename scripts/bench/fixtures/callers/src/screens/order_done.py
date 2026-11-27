from src.money import format_money
from src.orders import subtotal

STORE = "busan"


def render(order):
    return f"주문완료 {format_money(order['total'])}"
