import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, cast

import numpy
import pandas
import pyomo.environ as pyo
import requests
import tomlkit
from bs4 import BeautifulSoup, Tag

from velogames.rider import Rider

CSV = Path("riders.csv")


def obj_function(model: Any) -> Any:
    return pyo.summation(model.score, model.chosen)


def cost_rule(model: Any) -> bool:
    s: int = sum(model.chosen[i] * model.cost[i] for i in model.riders)
    return s <= 100


def choice_rule(model: Any) -> bool:
    s: int = sum(model.chosen[i] for i in model.riders)
    return s == 9


def classics_choice_rule(model: Any) -> bool:
    s: int = sum(model.chosen[i] for i in model.riders)
    return s == 6


def all_rounder_rule(model: Any) -> bool:
    s: int = sum(model.leaders[i] * model.chosen[i] for i in model.riders)
    return s >= 2


def climber_rule(model: Any) -> bool:
    s: int = sum(model.climbers[i] * model.chosen[i] for i in model.riders)
    return s >= 2


def sprinter_rule(model: Any) -> bool:
    s: int = sum(model.sprinters[i] * model.chosen[i] for i in model.riders)
    return s >= 1


def unclassed_rule(model: Any) -> bool:
    s: int = sum(model.unclassed[i] * model.chosen[i] for i in model.riders)
    return s >= 3


class GameType(Enum):
    GRAND_TOUR = 1
    STAGE_RACE = 2
    CLASSICS = 3
    CLASSICS_WITH_UNLIMITED_CHANGES = 4


class GameConfig(TypedDict):
    name: str
    url: str
    score_url: Optional[str]
    type: str
    tab: Dict[str, int]


class Computer:
    def __init__(self, *, csv: Optional[str] = None, config: Optional[str] = None):
        if config is None:
            config = "velogame.toml"
        cfg = tomlkit.parse(Path(config).read_text())
        self.cfg = cast(Dict[str, GameConfig], cfg)
        self.game_type = GameType[self.cfg["game"]["type"]]
        if csv is None:
            self.scrap()
            f = CSV
        else:
            f = Path(csv)
        if self.is_grand_tour:
            self.riders = pandas.read_csv(
                f, names=["name", "team", "class", "score", "cost"]
            )
        else:
            self.riders = pandas.read_csv(f, names=["name", "team", "score", "cost"])
        self.model = pyo.AbstractModel()
        self.init()

    @property
    def is_grand_tour(self) -> bool:
        return self.game_type == GameType.GRAND_TOUR

    def init(self) -> None:
        if self.is_grand_tour:
            for rider_class in self.riders["class"].unique():
                self.riders[rider_class] = numpy.where(
                    self.riders["class"] == rider_class, 1, 0
                )

        self.model.riders = pyo.Set(initialize=range(len(self.riders)))
        self.model.chosen = pyo.Var(
            self.model.riders, domain=pyo.Boolean
        )  # 1 for chosen, 0 otherwise
        self.model.score = pyo.Param(
            self.model.riders,
            domain=pyo.NonNegativeIntegers,
            initialize=self.riders.score.to_dict(),
        )
        self.model.cost = pyo.Param(
            self.model.riders,
            domain=pyo.NonNegativeIntegers,
            initialize=self.riders.cost.to_dict(),
        )
        if self.is_grand_tour:
            self.model.leaders = pyo.Param(
                self.model.riders,
                domain=pyo.Boolean,
                initialize=self.riders["All Rounder"].to_dict(),
            )
            self.model.climbers = pyo.Param(
                self.model.riders,
                domain=pyo.Boolean,
                initialize=self.riders["Climber"].to_dict(),
            )
            self.model.sprinters = pyo.Param(
                self.model.riders,
                domain=pyo.Boolean,
                initialize=self.riders["Sprinter"].to_dict(),
            )
            self.model.unclassed = pyo.Param(
                self.model.riders,
                domain=pyo.Boolean,
                initialize=self.riders["Unclassed"].to_dict(),
            )

        self.model.obj = pyo.Objective(rule=obj_function, sense=pyo.maximize)
        self.model.cost_constraint = pyo.Constraint(rule=cost_rule)
        if self.game_type == GameType.CLASSICS_WITH_UNLIMITED_CHANGES:
            self.model.choice_constraint = pyo.Constraint(rule=classics_choice_rule)
        else:
            self.model.choice_constraint = pyo.Constraint(rule=choice_rule)
        if self.is_grand_tour:
            self.model.all_rounder_constraint = pyo.Constraint(rule=all_rounder_rule)
            self.model.climber_constraint = pyo.Constraint(rule=climber_rule)
            self.model.sprinter_constraint = pyo.Constraint(rule=sprinter_rule)
            self.model.unclassed_constraint = pyo.Constraint(rule=unclassed_rule)

    def load_classics_score(self) -> None:
        # very brittle atm
        url = self.cfg["game"].get("score_url")
        assert url is not None
        res = requests.get(url).text
        soup = BeautifulSoup(res, features="html.parser")
        uls = soup.find_all("ul")
        ul = cast(Tag, uls[12])
        self.scores = {}
        for line in ul.find_all("li"):
            line = cast(Tag, line)
            name = cast(Tag, line.find_all("a")[0]).string
            score_span = cast(Tag, line.find_all("span")[1])
            score = int(
                cast(str, cast(Tag, cast(Tag, score_span.p).b).string).rstrip(" points")
            )
            self.scores[name] = score

    def scrap(self) -> None:
        res = requests.get(self.cfg["game"]["url"]).text
        if self.game_type == GameType.CLASSICS_WITH_UNLIMITED_CHANGES:
            self.load_classics_score()
        soup = BeautifulSoup(res, features="html.parser")
        tables = soup.find_all("table")
        assert len(tables) == 1
        table = cast(Tag, tables[0])
        tbodys = table.find_all("tbody")
        assert len(tbodys) == 1
        tbody = cast(Tag, tbodys[0])
        lines = []
        cfg = self.cfg["game"]["tab"]
        iname = cfg["name"]
        iteam = cfg["team"]
        if self.game_type != GameType.CLASSICS_WITH_UNLIMITED_CHANGES:
            iscore = cfg["score"]
        icost = cfg["cost"]
        if self.is_grand_tour:
            iclass = cfg["class"]
        for rider in tbody.find_all("tr"):
            rider = cast(Tag, rider)
            attrs = rider.find_all("td")
            name = cast(str, cast(Tag, attrs[iname]).string).strip()
            team = cast(str, cast(Tag, attrs[iteam]).string).strip()
            if self.game_type == GameType.CLASSICS_WITH_UNLIMITED_CHANGES:
                score = self.scores.get(name, 0)
            else:

                score = int(cast(str, cast(Tag, attrs[iscore]).string).strip())
            cost = int(cast(str, cast(Tag, attrs[icost]).string).strip())
            if self.is_grand_tour:
                rclass = cast(str, cast(Tag, attrs[iclass]).string).strip()
                r = Rider(name, team, score, cost, rclass)
            else:
                r = Rider(name, team, score, cost)
            lines.append(r.csv)
        CSV.write_text("\n".join(lines), encoding="utf-8")

    def compute(self) -> None:
        instance = self.model.create_instance()
        pyo.SolverFactory("glpk").solve(instance)
        self.riders["chosen"] = [
            bool(instance.chosen[i].value) for i in range(len(self.riders))
        ]
        self.team = self.riders[self.riders["chosen"]]

    def get_riders_text(self) -> str:
        text = ""
        if self.is_grand_tour:
            all_rounder_count = 0
            climber_count = 0
            sprinter_count = 0
            unclassed_count = 0
            all_rounders = [None, None]
            climbers = [None, None]
            sprinter = None
            unclassed = [None, None, None]
            wild_card = None
            for _, row in self.team.iterrows():
                if row["class"] == "All Rounder":
                    if all_rounder_count < len(all_rounders):
                        all_rounders[all_rounder_count] = row
                    else:
                        wild_card = row
                    all_rounder_count += 1
                if row["class"] == "Climber":
                    if climber_count < len(climbers):
                        climbers[climber_count] = row
                    else:
                        wild_card = row
                    climber_count += 1
                if row["class"] == "Sprinter":
                    if sprinter_count == 0:
                        sprinter = row
                    else:
                        wild_card = row
                    sprinter_count += 1
                if row["class"] == "Unclassed":
                    if unclassed_count < len(unclassed):
                        unclassed[unclassed_count] = row
                    else:
                        wild_card = row
                    unclassed_count += 1

            def to_str(table: List[Any]) -> str:
                res = ""
                for i in range(len(table)):
                    assert table[i] is not None
                    res += f"{table[i]['class'][0]} {i + 1}: {table[i]['name']}\n"
                return res

            text += to_str(all_rounders)
            text += to_str(climbers)
            assert sprinter is not None
            text += f"S: {sprinter['name']}\n"
            text += to_str(unclassed)
            assert wild_card is not None
            text += f"WC: {wild_card['name']}\n\n"
        else:
            for _, row in self.team.iterrows():
                text += f"{row['name']}\n"
        return text

    def publish(self, *, to_bsky: bool = True) -> None:
        score = self.riders[self.riders["chosen"]].score.sum()
        cost = self.riders[self.riders["chosen"]].cost.sum()
        game = self.cfg["game"]["name"]
        text = f"Best possible Velogames team for {game}:\n\n"
        text += self.get_riders_text()
        text += f"Score: {score}\n"
        text += f"Cost: {cost}"
        text_length = len(text)
        assert (
            text_length < 280
        ), f"text is too long for a tweet: {text_length} characters"
        print(text)
        if os.environ.get("CI") and to_bsky:
            pwd = os.environ["BSKY_PASSWORD"]
            handle = os.environ["BSKY_HANDLE"]
            bsky_session = requests.Session()
            res = bsky_session.post(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                json={
                    "identifier": handle,
                    "password": pwd,
                },
            )
            res.raise_for_status()
            res_json = res.json()
            token = res_json["accessJwt"]
            did = res_json["did"]
            bsky_session.headers.update({"Authorization": f"Bearer {token}"})
            res = bsky_session.post(
                "https://bsky.social/xrpc/com.atproto.repo.createRecord",
                json={
                    "repo": did,
                    "collection": "app.bsky.feed.post",
                    "record": {
                        "$type": "app.bsky.feed.post",
                        "text": text,
                        "createdAt": datetime.now(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                },
            )
            res.raise_for_status()
