from src.money import format_money
from src.orders import item_lines

STORE = "sf"


def render(order):
    amounts = [amount for _, amount in item_lines(order)] + [order["total"]]
    return "내보내기 " + " / ".join(map(format_money, amounts))
