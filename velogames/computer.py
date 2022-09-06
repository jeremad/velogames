import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, cast

import numpy
import pandas
import pyomo.environ as pyo
import requests
import tomlkit
import twitter
from bs4 import BeautifulSoup

from velogames.rider import Rider

CSV = Path("riders.csv")


def obj_function(model: Any) -> Any:
    return pyo.summation(model.score, model.chosen)


def cost_rule(model: Any) -> bool:
    return sum(model.chosen[i] * model.cost[i] for i in model.riders) <= 100


def choice_rule(model: Any) -> bool:
    return sum(model.chosen[i] for i in model.riders) == 9


def all_rounder_rule(model: Any) -> bool:
    return sum(model.leaders[i] * model.chosen[i] for i in model.riders) >= 2


def climber_rule(model: Any) -> bool:
    return sum(model.climbers[i] * model.chosen[i] for i in model.riders) >= 2


def sprinter_rule(model: Any) -> bool:
    return sum(model.sprinters[i] * model.chosen[i] for i in model.riders) >= 1


def unclassed_rule(model: Any) -> bool:
    return sum(model.unclassed[i] * model.chosen[i] for i in model.riders) >= 3


class GameType(Enum):
    GRAND_TOUR = 1
    STAGE_RACE = 2
    CLASSICS = 3
    CLASSICS_WITH_UNLIMITED_CHANGES = 4


class GameConfig(TypedDict):
    name: str
    url: str
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
        self.model.choice_constraint = pyo.Constraint(rule=choice_rule)
        if self.is_grand_tour:
            self.model.all_rounder_constraint = pyo.Constraint(rule=all_rounder_rule)
            self.model.climber_constraint = pyo.Constraint(rule=climber_rule)
            self.model.sprinter_constraint = pyo.Constraint(rule=sprinter_rule)
            self.model.unclassed_constraint = pyo.Constraint(rule=unclassed_rule)

    def scrap(self) -> None:
        res = requests.get(self.cfg["game"]["url"]).text
        soup = BeautifulSoup(res, features="html.parser")
        tables = soup.find_all("table")
        assert len(tables) == 1
        table = tables[0]
        tbodys = table.find_all("tbody")
        assert len(tbodys) == 1
        tbody = tbodys[0]
        lines = []
        cfg = self.cfg["game"]["tab"]
        iname = cfg["name"]
        iteam = cfg["team"]
        iscore = cfg["score"]
        icost = cfg["cost"]
        if self.is_grand_tour:
            iclass = cfg["class"]
        for rider in tbody.find_all("tr"):
            attrs = rider.find_all("td")
            name = attrs[iname].string
            team = attrs[iteam].string
            score = int(attrs[iscore].string)
            cost = int(attrs[icost].string)
            if self.is_grand_tour:
                rclass = attrs[iclass].string
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
            text += f"S {sprinter['name']}\n"
            text += to_str(unclassed)
            assert wild_card is not None
            text += f"WC: {wild_card['name']}\n\n"
        else:
            for _, row in self.team.iterrows():
                text += f"{row['name']}\n"
        return text

    def publish(self, *, to_twitter: bool = True) -> None:
        score = self.riders[self.riders["chosen"]].score.sum()
        cost = self.riders[self.riders["chosen"]].cost.sum()
        game = self.cfg["game"]["name"]
        text = f"Best possible team for {game}:\n\n"
        text += self.get_riders_text()
        text += f"Score: {score}\n"
        text += f"Cost: {cost}"
        text_length = len(text)
        assert (
            text_length < 280
        ), f"text is too long for a tweet: {text_length} characters"
        print(text)
        if os.environ.get("CI") and to_twitter:
            twitter_api = twitter.Api(
                consumer_key=os.environ["CONSUMER_KEY"],
                consumer_secret=os.environ["CONSUMER_SECRET"],
                access_token_key=os.environ["ACCESS_TOKEN_KEY"],
                access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
            )
            twitter_api.PostUpdate(text)
