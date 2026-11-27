from dataclasses import dataclass


@dataclass
class SlotFilter:
    name: str
    weight: int = 39

    def filter(self, other):
        return SlotFilter(self.name, self.weight + other.weight)
