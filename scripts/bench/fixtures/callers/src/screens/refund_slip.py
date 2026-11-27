from src.template import render_template

STORE = "seoul"


def render(order):
    return render_template("refund.txt", total=order["total"], rate=order["rate"])
