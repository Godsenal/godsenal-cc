from dataclasses import dataclass


@dataclass
class LevelFilter:
    name: str
    weight: int = 31

    def filter(self, other):
        return LevelFilter(self.name, self.weight + other.weight)
