from src import money

STORE = "sf"


def render(order):
    return "팁 " + money.format_money(order["total"])
