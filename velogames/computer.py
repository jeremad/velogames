from enum import Enum
import os
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict, cast

from bs4 import BeautifulSoup
import numpy
import pandas
import pyomo.environ as pyo
import requests
import tomlkit
import twitter

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
        CSV.write_text("\n".join(lines))

    def compute(self) -> None:
        instance = self.model.create_instance()
        pyo.SolverFactory("glpk").solve(instance)
        self.riders["chosen"] = [
            bool(instance.chosen[i].value) for i in range(len(self.riders))
        ]
        self.team = self.riders[self.riders["chosen"]]

    def publish(self, *, to_twitter: bool = True) -> None:
        score = self.riders[self.riders["chosen"]].score.sum()
        cost = self.riders[self.riders["chosen"]].cost.sum()
        game = self.cfg["game"]["name"]
        text = f"Best possible team for {game}:\n\n"
        for _, row in self.team.iterrows():
            text += f"{row['name']}\n"
        text += f"Score: {score}\n"
        text += f"Cost: {cost}"
        print(text)
        if os.environ.get("CI") and to_twitter:
            twitter_api = twitter.Api(
                consumer_key=os.environ["CONSUMER_KEY"],
                consumer_secret=os.environ["CONSUMER_SECRET"],
                access_token_key=os.environ["ACCESS_TOKEN_KEY"],
                access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
            )
            twitter_api.PostUpdate(text)
