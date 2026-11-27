def label_coupons(coupons, key="coupon_id"):
    """Label coupons by {key}."""
    out = {}
    for coupon in coupons:
        out.setdefault(coupon.get(key), []).append(coupon)
    return out
