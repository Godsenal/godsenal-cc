from src.pricing import line_total


def cart_total(items, coupon=None):
    total = sum(line_total(i) for i in items)
    if coupon:
        total = total - coupon
    return total
