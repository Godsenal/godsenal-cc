import sys

from src.pos.stock_reader import read_stock


def low(stock, threshold=5):
    return sorted(name for name, qty in stock.values() if qty < threshold)


if __name__ == "__main__":
    print("\n".join(low(read_stock(sys.argv[2], sys.argv[1]))))
