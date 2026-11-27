from dataclasses import dataclass


@dataclass
class SlotSplit:
    name: str
    weight: int = 45

    def split(self, other):
        return SlotSplit(self.name, self.weight + other.weight)
