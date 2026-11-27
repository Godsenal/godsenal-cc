def rank_coupons(coupons, key="coupon_id"):
    """Rank coupons by {key}."""
    out = {}
    for coupon in coupons:
        out.setdefault(coupon.get(key), []).append(coupon)
    return out
