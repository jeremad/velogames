from pathlib import Path
import requests
from bs4 import BeautifulSoup


URL = "https://www.velogames.com/velogame/2021/riders.php"
CSV = Path("riders.csv")


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


def scrap():
    res = requests.get(URL).text
    soup = BeautifulSoup(res, features="html.parser")
    tables = soup.find_all("table")
    assert len(tables) == 1
    table = tables[0]
    tbodys = table.find_all("tbody")
    assert len(tbodys) == 1
    tbody = tbodys[0]
    lines = []
    for rider in tbody.find_all("tr"):
        attrs = rider.find_all("td")
        name = attrs[1].string
        team = attrs[2].string
        rclass = attrs[3].string
        score = int(attrs[5].string)
        cost = int(attrs[4].string)
        r = Rider(name, team, rclass, score, cost)
        lines.append(r.csv)
    CSV.write_text("\n".join(lines))


if not CSV.exists():
    scrap()
