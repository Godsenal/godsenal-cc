def split_bill(total_cents, n):
    """Split total_cents among n people. The rules are in docs/split-rules.md."""
    share = total_cents // n
    return [share] * n
