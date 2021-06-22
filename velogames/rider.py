from enum import Enum


class RiderClass(Enum):
    LEADER = 1
    CLIMBER = 2
    SPRINTER = 3
    UNCLASSED = 4

    @classmethod
    def from_str(cls, label):
        if label in ["All Rounder", "LEADER"]:
            return cls.LEADER
        if label in ["Climber", "CLIMBER"]:
            return cls.CLIMBER
        if label in ["Sprinter", "SPRINTER"]:
            return cls.SPRINTER
        if label in ["Unclassed", "UNCLASSED"]:
            return cls.UNCLASSED
        raise NotImplementedError

    def __str__(self):
        if self == self.LEADER:
            return "LEADER"
        if self == self.CLIMBER:
            return "CLIMBER"
        if self == self.SPRINTER:
            return "SPRINTER"
        if self == self.UNCLASSED:
            return "UNCLASSED"
        raise NotImplementedError


class Rider:
    def __init__(self, name: str, team: str, rclass: str, score: int, cost: int):
        self.name = name
        self.team = team
        self.rclass = RiderClass.from_str(rclass)
        self.score = score
        self.cost = cost

    def __eq__(self, other):
        return other.name == self.name

    def __ne__(self, other):
        return other.name != self.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    @property
    def csv(self):
        return ";".join([self.name, self.team, str(self.rclass), str(self.score), str(self.cost)])

    @classmethod
    def from_csv_line(cls, line):
        data = line.split(";")
        return cls(data[0], data[1], data[2], int(data[3]), int(data[4]))
