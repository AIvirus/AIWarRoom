# Mini project: how much cash will a new chai stall have, month by month?
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StallPlan:
    price_per_cup: Decimal
    cost_per_cup: Decimal
    cups_per_month: Decimal
    rent_per_month: Decimal
    starting_cash: Decimal


@dataclass(frozen=True)
class Month:
    number: int
    profit: Decimal
    cash: Decimal


def simulate(plan: StallPlan, months: int) -> list[Month]:
    """Cash at the end of each month: last month's cash + this month's profit."""
    results = []
    cash = plan.starting_cash
    for number in range(1, months + 1):
        profit = (
            plan.cups_per_month * (plan.price_per_cup - plan.cost_per_cup) - plan.rent_per_month
        )
        cash = cash + profit
        results.append(Month(number, profit, cash))
    return results


def first_month_out_of_cash(months: list[Month]) -> int | None:
    for month in months:
        if month.cash < 0:
            return month.number
    return None


if __name__ == "__main__":
    plan = StallPlan(
        price_per_cup=Decimal("15"),
        cost_per_cup=Decimal("6.5"),
        cups_per_month=Decimal("1500"),
        rent_per_month=Decimal("15000"),
        starting_cash=Decimal("20000"),
    )
    for month in simulate(plan, 6):
        print(f"Month {month.number}: profit {month.profit}, cash {month.cash}")
    print("Runs out of cash in month:", first_month_out_of_cash(simulate(plan, 24)))
