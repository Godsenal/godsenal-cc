CARRIERS = {"seoul": "cj", "nyc": "ups", "tokyo": "yamato"}


def carrier(order):
    return CARRIERS.get(order["store"], "post")
