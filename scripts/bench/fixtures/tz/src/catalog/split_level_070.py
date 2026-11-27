from dataclasses import dataclass


@dataclass
class LevelSplit:
    name: str
    weight: int = 11

    def split(self, other):
        return LevelSplit(self.name, self.weight + other.weight)
