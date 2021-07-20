from typing import Optional


class Rider:
    def __init__(
        self, name: str, team: str, score: int, cost: int, rclass: Optional[str] = None
    ):
        self.name = name
        self.team = team
        self.score = score
        self.cost = cost
        self.rclass = rclass

    @property
    def csv(self):
        if self.rclass is not None:
            res = ",".join(
                [
                    self.name,
                    self.team,
                    str(self.rclass),
                    str(self.score),
                    str(self.cost),
                ]
            )
        else:
            res = ",".join([self.name, self.team, str(self.score), str(self.cost)])
        return res
