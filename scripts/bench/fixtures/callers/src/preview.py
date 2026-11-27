import importlib
import pkgutil

from src import screens

SAMPLE = {"items": [{"name": "coffee", "price": 120000, "qty": 1}, {"name": "cookie", "price": 3456, "qty": 1}],
          "total": 123456, "discount": 1000, "rate": 2.5}


def all_screens():
    for info in pkgutil.iter_modules(screens.__path__):
        yield importlib.import_module(f"src.screens.{info.name}")


if __name__ == "__main__":
    for mod in all_screens():
        print(f"--- {mod.__name__} ({mod.STORE})")
        print(mod.render(SAMPLE))
