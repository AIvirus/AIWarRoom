# Formulas and assumptions

Every number AI WarRoom shows comes from these formulas, implemented in
`simulation_engine/` (plain Python, `Decimal` arithmetic). Each worked example below is
also a test in `simulation_engine/tests/`, so it is checked on every run.

Percentages are written the way people say them: `22.5` means 22.5 %.

---

## 1. Idea Simulator (`idea.py`)

A month-by-month model of a business that hasn't launched.

| Quantity | Formula |
|---|---|
| Customer acquisition cost (CAC) | `cost_per_visit / conversion` |
| New customers per month | `marketing_spend / CAC` |
| Customers in month t | `customers(t-1) × retention + new customers` |
| Orders | `customers × orders_per_customer` |
| Revenue | `orders × price` |
| Gross profit | `orders × (price − variable_cost)` |
| Operating result | `gross profit − fixed_costs − marketing_spend` |
| Cash in month t | `cash(t-1) + operating result` (month 0 = initial investment) |
| Average customer lifetime | `1 / (1 − retention)` months (not shown at 100 % retention) |
| Lifetime value (LTV) | `(price − variable_cost) × orders_per_customer × lifetime` |
| Steady-state orders | `new customers / (1 − retention) × orders_per_customer` |
| Funding gap | `max(0, −lowest cash)` |

**Worked example** (`test_idea.py`). Price ₹500, variable cost ₹300, fixed ₹1,00,000,
marketing ₹50,000, cost per visit ₹10, conversion 2 %, retention 80 %, 2 orders per
customer, investment ₹10,00,000.

- CAC = 10 / 0.02 = **₹500**, so 50,000 / 500 = **100 new customers a month**.
- Month 1: 100 customers, 200 orders, gross profit ₹40,000, result **−₹1,10,000**.
- Month 2: 180 customers (80 + 100), 360 orders, result **−₹78,000**.
- Month 3: 244 customers, 488 orders, result **−₹52,400**; cash **₹7,59,600**.
- Lifetime 1/(1−0.8) = 5 months, so LTV = 200 × 2 × 5 = **₹2,000** and LTV/CAC = **4**.
- Customers in month t = 500 × (1 − 0.8ᵗ). Break-even needs 375 customers, which first
  happens in **month 7** (result +₹8,056.96).

**Funnel honesty check.** The founder's own expected orders are compared with what the
funnel supports by month 6. Expecting 1,000 when the model gives 737.86 means the
estimate is **26.21 % higher** than the inputs support.

**Not modelled:** price elasticity (price and demand move independently), taxes, payment
timing, seasonality, churn by cohort.

## 2. The seven cases (`cases.py`)

| Case | What changes (illustrative sizes) |
|---|---|
| Expected | Inputs as entered |
| Best | conversion ×1.2, retention +5 pts |
| Worst | conversion ×0.7, variable cost ×1.15, retention −10 pts |
| Reduced demand | orders per customer ×0.75 |
| Higher costs | variable cost ×1.15, fixed costs ×1.2 |
| Lower conversion | conversion ×0.7 |
| More competition | cost per visit ×1.4, price ×0.95 |

Rates are clamped to 0–100 %. These sizes are teaching defaults, not market research.

## 3. Sensitivity (`sensitivity.py`)

Each of eight inputs is moved down and up by the same step (default 10 %) while the others
stay as entered. **Swing** = |ending cash at +step − ending cash at −step|. Inputs are
sorted by swing; that's the tornado chart. Interactions between inputs are ignored.

---

## 4. Disruptions (`disruption.py`)

Hour by hour, starting when the outage starts. Demand per hour comes from either a uniform
day (`daily_orders / 24`) or an illustrative e-commerce curve with an evening peak.

**The key distinction:**

| Term | Meaning |
|---|---|
| Affected orders | Orders that hit the broken component |
| Lost orders | Affected orders that never complete |
| Lost revenue | `lost orders × average order value` |
| Lost contribution | `lost revenue × contribution margin`: what the P&L actually loses |
| Total impact | `lost contribution + cost of the response` |

### 4a. Checkout mode: payment gateway

Affected = `demand × share through the gateway × fraction of the hour it is down`.

| Strategy | Mechanics |
|---|---|
| Wait | Failed checkouts: `recapture %` return later and succeed; the rest are lost |
| Backup | After the switch-over delay, up to `backup capacity/hour` go through the backup at `extra cost/order` (+ one-off activation cost). The rest fail as in Wait |
| Queue & retry | Failed payments that would wait ≤ the retry window are queued; `retry success %` succeed. Everything still failed gets the same natural recapture as Wait, so the comparison is fair. Cost: `retry cost × queued` |

**Worked example** (`test_disruption.py`). 100 orders/hour, 100 % through the gateway,
2-hour outage, recapture 30 %, ₹600 per order, 25 % margin.

| | Wait | Backup (0.5 h switch, 60/h, ₹12/order, ₹5,000) | Queue & retry (55 %) |
|---|---|---|---|
| Affected | 200 | 200 | 200 |
| Recovered | 60 | 90 via backup + 33 recaptured = 123 | 110 retried + 27 recaptured = 137 |
| Lost | 140 | 77 | 63 |
| Lost revenue | ₹84,000 | ₹46,200 | ₹37,800 |
| Lost contribution | ₹21,000 | ₹11,550 | ₹9,450 |
| Response cost | ₹0 | ₹6,080 | ₹600 |
| **Total impact** | **₹21,000** | **₹17,630** | **₹10,050** |

### 4b. Fulfilment mode: warehouse, courier

Orders are taken but can't be processed. They wait in a first-in-first-out queue, and
capacity works from the front of the queue once service returns. An order delayed `d`
hours is cancelled with probability `min(max cancel %, cancel %/hour × d)`. Cancelled
orders use no capacity. Impact is measured **against the same business with no outage**,
so a business that is already short of capacity isn't blamed on the outage.

| Strategy | Mechanics |
|---|---|
| Wait | Backlog clears with normal capacity after the outage |
| Backup | During the outage, after the switch-over, backup capacity processes the queue |
| Queue & notify | Customers told "ships by X" keep `retry success %` of would-be cancellations for delays within the promise window. Cost per delayed order |

**Worked example.** 100 orders/hour, capacity 200/hour, 2-hour outage, cancellations
2 %/hour (max 30 %).

- Hours 0–1: nothing ships, and the queue reaches 200.
- Hour 2: 96 + 98 ship (4 + 2 cancelled); 6 of hour 2's orders ship, 94 wait.
- Hour 3: 92.12 ship (1.88 cancelled), and hour 3's 100 ship on time.
- Delayed 294, cancelled **7.88**, lost revenue ₹4,728, lost contribution **₹1,182**.
- Back to normal after **4 hours**.

### 4c. What the system view shows

Each component's health (0–1) per hour comes from the engine. The broken component's
health is served/demand (or capacity available/normal). Its **direct dependents** lose
`share × (1 − health)`. Failure spreads one step only; deeper cascades aren't modelled.

---

## 5. What the AI may say about these numbers

The guardrail (`intelligence/services/guardrails.py`) accepts a number in AI text only if
it equals a number we sent, rounded or truncated to the digits the AI wrote:

- "about ₹15k" for 14,700 passes;
- "₹14,550" doesn't, and neither does a difference the AI worked out itself.

Anything else is flagged as unverified in the UI.
