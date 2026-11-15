# Making decisions with if, and repeating work with for and while.
cups_sold = [110, 125, 98, 140, 160, 210, 190]
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

for day, cups in zip(days, cups_sold, strict=True):
    if cups >= 180:
        note = "busy"
    elif cups >= 120:
        note = "normal"
    else:
        note = "slow"
    print(day, cups, note)

savings = 0
months = 0
while savings < 50000:
    savings = savings + 12000
    months = months + 1
print("Months to save 50,000:", months)
