from src.money import format_money
from src.orders import item_lines

STORE = "sf"


def render(order):
    rows = [f"{name} {format_money(amount)}" for name, amount in item_lines(order)]
    rows.append(f"케이터링 {format_money(order['total'])}")
    return "\n".join(rows)
