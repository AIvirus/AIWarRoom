# Functions: give a name to a recipe so you can use it again.
def profit_for_day(cups, price=15, cost=6.5):
    """Money left after paying for the tea, milk and sugar."""
    money_in = cups * price
    money_out = cups * cost
    return money_in - money_out


print(profit_for_day(120))
print(profit_for_day(120, price=20))
print(profit_for_day(cups=50, cost=8))


def best_day(sales: dict[str, int]) -> str:
    """The day with the most cups sold."""
    best = None
    for day, cups in sales.items():
        if best is None or cups > sales[best]:
            best = day
    return best


print(best_day({"Mon": 110, "Sat": 210, "Sun": 190}))
