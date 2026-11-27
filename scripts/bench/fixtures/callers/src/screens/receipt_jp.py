from src.template import render_template

STORE = "tokyo"


def render(order):
    return render_template("receipt.txt", total=order["total"], rate=order["rate"])
