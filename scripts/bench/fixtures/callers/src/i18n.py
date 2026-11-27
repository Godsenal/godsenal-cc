LABELS = {"ko": {"total": "합계"}, "en": {"total": "Total"}, "ja": {"total": "合計"}}


def label(lang, key):
    return LABELS.get(lang, LABELS["ko"]).get(key, key)
