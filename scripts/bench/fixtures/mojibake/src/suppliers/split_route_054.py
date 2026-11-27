from dataclasses import dataclass


@dataclass
class RouteSplit:
    name: str
    weight: int = 3

    def split(self, other):
        return RouteSplit(self.name, self.weight + other.weight)
