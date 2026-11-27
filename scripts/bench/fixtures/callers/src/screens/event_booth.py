from src import money

STORE = "nyc"


def render(order):
    return "이벤트 " + money.format_money(order["total"])
