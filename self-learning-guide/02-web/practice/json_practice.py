# JSON: the text format websites and APIs use to send data.
import json

stall = {"name": "Raju Chai", "price_per_cup": 15, "open": True, "phone": None}

text = json.dumps(stall)
print(text)
print(type(text))

back = json.loads('{"name": "Meena Tea", "cups": [110, 125, 98]}')
print(back["name"], sum(back["cups"]))
print(type(back))
