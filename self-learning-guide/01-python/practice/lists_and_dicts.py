# Lists keep things in order. Dictionaries give names to values.
sales_this_week = [110, 125, 98, 140, 160, 210, 190]

print("Monday:", sales_this_week[0])
print("Sunday:", sales_this_week[-1])
print("Days recorded:", len(sales_this_week))
print("Total cups:", sum(sales_this_week))

sales_this_week.append(175)
print("After adding one more day:", sales_this_week)

stall = {
    "name": "Raju Chai",
    "price_per_cup": 15,
    "cost_per_cup": 6.5,
}
print(stall["name"], "sells chai at", stall["price_per_cup"])

stall["city"] = "Pune"
print("Keys:", list(stall.keys()))
print("Has a phone number?", "phone" in stall)
