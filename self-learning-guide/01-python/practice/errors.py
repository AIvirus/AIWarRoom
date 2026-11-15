# Errors happen. We can catch them and explain what went wrong.
def price_per_cup(total_money, cups):
    if cups < 0:
        raise ValueError("cups can't be negative")
    return total_money / cups


try:
    print(price_per_cup(1800, 120))
    print(price_per_cup(1800, 0))
except ZeroDivisionError:
    print("No cups sold, so there is no price per cup.")

try:
    price_per_cup(1800, -5)
except ValueError as error:
    print("Problem:", error)

try:
    int("fifteen")
except ValueError as error:
    print("Couldn't read the number:", error)
