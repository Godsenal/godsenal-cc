HOURS = {"seoul": (8, 22), "busan": (9, 21), "jeju": (10, 20), "nyc": (7, 23), "sf": (7, 21),
         "tokyo": (8, 22), "osaka": (9, 22)}


def is_open(store, hour):
    start, end = HOURS[store]
    return start <= hour < end
