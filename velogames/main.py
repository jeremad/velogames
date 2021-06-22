import numpy
import pandas
import pyomo.environ as pyo


from velogames.scrapper import scrap, CSV


def obj_function(model):
    return pyo.summation(model.y, model.x)


def cost_rule(model):
    return sum(model.x[i] * model.z[i] for i in model.R) <= 100


def choice_rule(model):
    return sum(model.x[i] for i in model.R) == 9


def all_rounder_rule(model):
    return sum(model.a[i] * model.x[i] for i in model.R) >= 2


def climber_rule(model):
    return sum(model.c[i] * model.x[i] for i in model.R) >= 2


def sprinter_rule(model):
    return sum(model.s[i] * model.x[i] for i in model.R) >= 1


def unclassed_rule(model):
    return sum(model.u[i] * model.x[i] for i in model.R) >= 3


def main():
    if not CSV.exists():
        scrap()
    riders = pandas.read_csv(CSV, names=["name", "team", "class", "score", "cost"])
    for rider_class in riders["class"].unique():
        riders[rider_class] = numpy.where(riders["class"] == rider_class, 1, 0)

    model = pyo.AbstractModel()
    model.R = pyo.Set(initialize=range(len(riders)))
    model.x = pyo.Var(model.R, domain=pyo.Boolean)
    model.y = pyo.Param(
        model.R, domain=pyo.NonNegativeIntegers, initialize=riders.score.to_dict()
    )
    model.z = pyo.Param(
        model.R, domain=pyo.NonNegativeIntegers, initialize=riders.cost.to_dict()
    )
    model.a = pyo.Param(
        model.R, domain=pyo.Boolean, initialize=riders["All Rounder"].to_dict()
    )
    model.c = pyo.Param(
        model.R, domain=pyo.Boolean, initialize=riders["Climber"].to_dict()
    )
    model.s = pyo.Param(
        model.R, domain=pyo.Boolean, initialize=riders["Sprinter"].to_dict()
    )
    model.u = pyo.Param(
        model.R, domain=pyo.Boolean, initialize=riders["Unclassed"].to_dict()
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
    riders["chosen"] = [bool(instance.x[i].value) for i in range(len(riders))]
    print(riders[riders["chosen"]][["name", "class", "team", "cost", "score"]])
