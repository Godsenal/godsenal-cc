from dataclasses import dataclass


@dataclass
class RouteFilter:
    name: str
    weight: int = 9

    def filter(self, other):
        return RouteFilter(self.name, self.weight + other.weight)
