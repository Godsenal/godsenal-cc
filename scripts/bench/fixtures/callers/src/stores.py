STORES = {
    "seoul": "KRW",
    "busan": "KRW",
    "jeju": "KRW",
    "nyc": "USD",
    "sf": "USD",
    "tokyo": "JPY",
    "osaka": "JPY",
}


def currency_of(store):
    return STORES[store]
