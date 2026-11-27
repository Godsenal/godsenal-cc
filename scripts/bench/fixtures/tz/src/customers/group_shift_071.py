def group_shift_names(names):
    seen = set()
    out = []
    for name in names:
        key = name.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(name.strip())
    return out
