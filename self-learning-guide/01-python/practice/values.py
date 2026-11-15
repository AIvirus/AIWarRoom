# A tiny chai stall, described with values.
stall_name = "Raju Chai"
cups_per_day = 120
price_per_cup = 15
cost_per_cup = 6.5
is_open_today = True
owner_phone = None

money_in = cups_per_day * price_per_cup
money_out = cups_per_day * cost_per_cup
profit = money_in - money_out

print(stall_name)
print("Money in today:", money_in)
print("Profit today:", profit)
print(f"{stall_name} made {profit} rupees profit from {cups_per_day} cups.")
print(type(cups_per_day), type(cost_per_cup), type(stall_name), type(is_open_today))
