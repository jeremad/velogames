class Rider:
    def __init__(self, name: str, team: str, rclass: str, score: int, cost: int):
        self.name = name
        self.team = team
        self.rclass = rclass
        self.score = score
        self.cost = cost

    @property
    def csv(self):
        return ",".join(
            [self.name, self.team, str(self.rclass), str(self.score), str(self.cost)]
        )
