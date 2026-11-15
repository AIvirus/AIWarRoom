# Classes: a blueprint for things that have data and can do things.
from dataclasses import dataclass, replace


class Stall:
    def __init__(self, name, price_per_cup):
        self.name = name
        self.price_per_cup = price_per_cup

    def money_in(self, cups):
        return cups * self.price_per_cup


raju = Stall("Raju Chai", 15)
print(raju.name, raju.money_in(100))


@dataclass(frozen=True)
class Plan:
    price: int
    cups_per_day: int

    def daily_sales(self):
        return self.price * self.cups_per_day


plan = Plan(price=15, cups_per_day=120)
print(plan)
print(plan.daily_sales())

bigger = replace(plan, cups_per_day=200)
print(bigger.daily_sales(), "versus", plan.daily_sales())
