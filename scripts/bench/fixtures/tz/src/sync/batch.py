def batches(items, size=100):
    return [items[i:i + size] for i in range(0, len(items), size)]
