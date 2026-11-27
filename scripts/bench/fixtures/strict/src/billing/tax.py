from src.billing.rates import VAT_PERCENT


def vat(amount_won):
    """VAT on a price in won, rounded half up to a whole won."""
    return round(amount_won * VAT_PERCENT / 100)
