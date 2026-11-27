from src.format_registry import format_cell

STORE = "nyc"
COLUMNS = [("합계", "money", "total"), ("할인", "money", "discount"), ("적립률", "pct", "rate")]


def render(order):
    return "멤버십 " + " · ".join(f"{label} {format_cell(kind, order[key])}" for label, kind, key in COLUMNS)
