import os

import pandas
import pyomo.environ as pyo
import twitter

from velogames.scrapper import CSV


def obj_function(model):
    return pyo.summation(model.score, model.chosen)


def cost_rule(model):
    return sum(model.chosen[i] * model.cost[i] for i in model.riders) <= 100


def choice_rule(model):
    return sum(model.chosen[i] for i in model.riders) == 9


class Computer:
    def __init__(self):
        self.twitter_api = twitter.Api(
            consumer_key=os.environ["CONSUMER_KEY"],
            consumer_secret=os.environ["CONSUMER_SECRET"],
            access_token_key=os.environ["ACCESS_TOKEN_KEY"],
            access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
        )
        self.riders = pandas.read_csv(CSV, names=["name", "team", "score", "cost"])
        self.model = pyo.AbstractModel()
        self.init()

    def init(self):
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

        self.model.obj = pyo.Objective(rule=obj_function, sense=pyo.maximize)
        self.model.cost_constraint = pyo.Constraint(rule=cost_rule)
        self.model.choice_constraint = pyo.Constraint(rule=choice_rule)

    def compute(self):
        instance = self.model.create_instance()
        pyo.SolverFactory("glpk").solve(instance)
        self.riders["chosen"] = [
            bool(instance.chosen[i].value) for i in range(len(self.riders))
        ]
        self.team = self.riders[self.riders["chosen"]]

    def publish(self):
        score = self.riders[self.riders["chosen"]].score.sum()
        cost = self.riders[self.riders["chosen"]].cost.sum()
        text = "Best possible team:\n"
        for _, row in self.team.iterrows():
            text += f"{row['name']}\n"
        text += f"Score: {score}\n"
        text += f"Cost: {cost}"
        print(text)
        self.twitter_api.PostUpdate(text)
