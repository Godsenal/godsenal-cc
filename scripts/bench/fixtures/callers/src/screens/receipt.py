from src.template import render_template

STORE = "nyc"


def render(order):
    return render_template("receipt.txt", total=order["total"], rate=order["rate"])
