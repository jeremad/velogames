import numpy
import pandas
import pyomo.environ as pyo


from velogames.scrapper import scrap, CSV


def obj_function(model):
    return pyo.summation(model.score, model.chosen)


def cost_rule(model):
    return sum(model.chosen[i] * model.cost[i] for i in model.riders) <= 100


def choice_rule(model):
    return sum(model.chosen[i] for i in model.riders) == 9


def all_rounder_rule(model):
    return sum(model.leaders[i] * model.chosen[i] for i in model.riders) >= 2


def climber_rule(model):
    return sum(model.climbers[i] * model.chosen[i] for i in model.riders) >= 2


def sprinter_rule(model):
    return sum(model.sprinters[i] * model.chosen[i] for i in model.riders) >= 1


def unclassed_rule(model):
    return sum(model.unclassed[i] * model.chosen[i] for i in model.riders) >= 3


def main():
    if not CSV.exists():
        scrap()
    riders = pandas.read_csv(CSV, names=["name", "team", "class", "score", "cost"])
    for rider_class in riders["class"].unique():
        riders[rider_class] = numpy.where(riders["class"] == rider_class, 1, 0)

    model = pyo.AbstractModel()
    model.riders = pyo.Set(initialize=range(len(riders)))
    model.chosen = pyo.Var(
        model.riders, domain=pyo.Boolean
    )  # 1 for chosen, 0 otherwise
    model.score = pyo.Param(
        model.riders, domain=pyo.NonNegativeIntegers, initialize=riders.score.to_dict()
    )
    model.cost = pyo.Param(
        model.riders, domain=pyo.NonNegativeIntegers, initialize=riders.cost.to_dict()
    )
    model.leaders = pyo.Param(
        model.riders, domain=pyo.Boolean, initialize=riders["All Rounder"].to_dict()
    )
    model.climbers = pyo.Param(
        model.riders, domain=pyo.Boolean, initialize=riders["Climber"].to_dict()
    )
    model.sprinters = pyo.Param(
        model.riders, domain=pyo.Boolean, initialize=riders["Sprinter"].to_dict()
    )
    model.unclassed = pyo.Param(
        model.riders, domain=pyo.Boolean, initialize=riders["Unclassed"].to_dict()
    )

    model.obj = pyo.Objective(rule=obj_function, sense=pyo.maximize)
    model.cost_constraint = pyo.Constraint(rule=cost_rule)
    model.choice_constraint = pyo.Constraint(rule=choice_rule)
    model.all_rounder_constraint = pyo.Constraint(rule=all_rounder_rule)
    model.climber_constraint = pyo.Constraint(rule=climber_rule)
    model.sprinter_constraint = pyo.Constraint(rule=sprinter_rule)
    model.unclassed_constraint = pyo.Constraint(rule=unclassed_rule)

    instance = model.create_instance()
    pyo.SolverFactory("glpk").solve(instance)
    riders["chosen"] = [bool(instance.chosen[i].value) for i in range(len(riders))]
    team = riders[riders["chosen"]]
    score = riders[riders["chosen"]].score.sum()
    cost = riders[riders["chosen"]].cost.sum()

    print("Best possible team:")
    for _, row in team.iterrows():
        print(row["name"])
    print("Score:", score)
    print("Cost:", cost)
