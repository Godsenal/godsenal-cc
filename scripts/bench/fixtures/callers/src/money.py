def format_money(amount):
    """An amount in won with thousands separators: format_money(1234) == "1,234원"."""
    return f"{amount:,}원"


def format_pct(value):
    return f"{value:.1f}%"
