from src.money import format_money
from src.orders import item_lines

STORE = "osaka"


def render(order):
    amounts = [amount for _, amount in item_lines(order)] + [order["total"]]
    return "대량주문 " + " / ".join(map(format_money, amounts))
