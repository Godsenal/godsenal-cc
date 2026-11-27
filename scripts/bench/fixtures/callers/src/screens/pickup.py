from src import money

STORE = "osaka"


def render(order):
    return "픽업 " + money.format_money(order["total"])
