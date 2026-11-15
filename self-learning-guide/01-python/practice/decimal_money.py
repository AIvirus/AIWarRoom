# Why money needs Decimal, not float.
from decimal import ROUND_HALF_UP, Decimal

print(0.1 + 0.2)
print(Decimal("0.1") + Decimal("0.2"))

price = Decimal("19.99")
cups = 3
total = price * cups
print(total)

tax = total * Decimal("0.18")
print(tax)
print(tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

print(Decimal(0.1))
