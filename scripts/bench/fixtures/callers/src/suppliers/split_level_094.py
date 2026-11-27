from dataclasses import dataclass


@dataclass
class LevelSplit:
    name: str
    weight: int = 23

    def split(self, other):
        return LevelSplit(self.name, self.weight + other.weight)
