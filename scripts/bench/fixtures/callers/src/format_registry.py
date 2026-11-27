from src import money

FORMATTERS = {
    "money": money.format_money,
    "pct": money.format_pct,
    "text": str,
}


def format_cell(kind, value):
    return FORMATTERS[kind](value)
