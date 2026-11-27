def segment(total_spent):
    if total_spent >= 1_000_000:
        return "vip"
    return "regular" if total_spent >= 100_000 else "new"
