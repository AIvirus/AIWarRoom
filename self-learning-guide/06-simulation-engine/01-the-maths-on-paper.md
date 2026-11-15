# 6.1 · The maths on paper

**Time:** 40 minutes · **Before this:** [Part 5](../05-business-and-api/README.md).
**No typing in this lesson.** Get a pencil, paper and a calculator (your phone is fine).

## 📖 Read

A computer model is only worth trusting if a person can check it. So before any code,
you'll work out two answers **by hand**. In lesson 6.9 the tests check that the code gets
**exactly** the same numbers.

## Example 1: a tiffin idea, month by month

Priya wants to start a tiffin (lunch box) service. Her numbers:

| Number | Value |
|---|---|
| Price per order | ₹500 |
| Variable cost per order (food, box, delivery) | ₹300 |
| Fixed costs (kitchen rent, salaries) | ₹1,00,000 a month |
| Marketing spend | ₹50,000 a month |
| Cost per visit (what an ad costs to bring one person to her page) | ₹10 |
| Conversion (visitors who become customers) | 2 % |
| Orders per customer per month | 2 |
| Monthly retention (customers who stay next month) | 80 % |
| Initial investment (money she starts with) | ₹10,00,000 |

### Step 1: what does one customer cost?

If 2 % of visitors become customers, she needs 100 ÷ 2 = **50 visits** for one customer.
50 visits × ₹10 = **₹500**. This is the **customer acquisition cost (CAC)**:

```text
CAC = cost per visit ÷ conversion = 10 ÷ 0.02 = 500
```

### Step 2: how many new customers a month?

```text
new customers = marketing ÷ CAC = 50,000 ÷ 500 = 100
```

### Step 3: play the months forward

Each month: 80 % of last month's customers stay, and 100 new ones arrive.

| Month | Customers | Orders (× 2) | Gross profit (orders × ₹200) | Result (− ₹1,50,000 costs) | Cash |
|---|---|---|---|---|---|
| start | 0 | | | | 10,00,000 |
| 1 | 0 × 0.8 + 100 = **100** | 200 | 40,000 | **−1,10,000** | 8,90,000 |
| 2 | 100 × 0.8 + 100 = **180** | 360 | 72,000 | **−78,000** | 8,12,000 |
| 3 | 180 × 0.8 + 100 = **244** | 488 | 97,600 | **−52,400** | **7,59,600** |

(₹200 is the **contribution per order**: price 500 − variable cost 300. ₹1,50,000 is
fixed costs + marketing.)

Fill in month 4 yourself before you read on. *(Answer: 295.2 customers, 590.4 orders,
gross profit 1,18,080, result −31,920, cash 7,27,680.)*

Customers can be a fraction like 295.2. That's fine: the model works with **averages**
("on average 295.2 customers"). Screens round them.

### Step 4: where does it level off?

Customers stop growing when the 20 % who leave equals the 100 who join:
`customers × 0.2 = 100`, so **500 customers**, or 1,000 orders a month. Then gross profit
is 1,000 × 200 = 2,00,000, more than the 1,50,000 of costs. So Priya **will** become
profitable. When? Month 7, it turns out (lesson 6.9's test shows the working).

### Step 5: is a customer worth what they cost?

A customer who stays with 80 % chance each month stays, on average, 1 ÷ (1 − 0.8) =
**5 months**. In 5 months they bring 5 × 2 orders × ₹200 = **₹2,000**: the
**lifetime value (LTV)**. LTV ÷ CAC = 2,000 ÷ 500 = **4**. A common rule of thumb says
above 3 is healthy.

## Example 2: a payment gateway goes down

Kirana Express sells 2,400 orders a day, spread evenly: **100 orders every hour**. Every
order pays through one gateway. The gateway stops for **2 hours**.

| Number | Value |
|---|---|
| Average order value | ₹600 |
| Contribution margin (what's left after variable costs) | 25 % |
| Recapture (customers who come back later and pay) | 30 % |

```text
affected orders    = 2 hours × 100            = 200 orders   (₹1,20,000 worth)
recovered          = 30 % of 200              = 60 orders    (they came back)
lost orders        = 200 − 60                 = 140 orders
lost revenue       = 140 × ₹600               = ₹84,000
lost contribution  = 25 % of ₹84,000          = ₹21,000      <- what the business really loses
```

Notice the three different numbers. A worried manager might say "we lost ₹1,20,000!".
In fact ₹1,20,000 of orders were **affected**, ₹84,000 of revenue was **lost**, and the
business is **₹21,000** worse off, because the goods it didn't sell also didn't cost it
anything. The engine always shows all three, clearly labelled.

### Now with a response: queue and retry

Instead of waiting, the shop **queues** the failed payments and retries them when the
gateway is back. Retries succeed 55 % of the time and cost ₹3 each.

```text
queued                 = 200
succeed on retry       = 55 % of 200 = 110
still failed           = 90; of those, 30 % come back anyway = 27
recovered              = 110 + 27 = 137;  lost = 200 − 137 = 63
lost contribution      = 63 × ₹600 × 25 % = ₹9,450
cost of the response   = 200 × ₹3 = ₹600
total impact           = ₹9,450 + ₹600 = ₹10,050
```

So queueing saves 21,000 − 10,050 = ₹10,950 compared with waiting. The engine works out
the third response, "switch to a backup gateway", the same way (lesson 6.5).

## Example 3 (for later): a warehouse queue

When a **warehouse** stops, orders don't fail; they **wait** in a queue. Each hour an
order waits, a few more customers cancel. When the warehouse comes back it clears the
queue, oldest orders first, using its spare capacity. Lesson 6.6 works through this one
hour by hour, because it needs a table to follow.

## ❓ Quiz

1. With conversion 4 % instead of 2 %, what is the CAC?
2. Retention 90 %: how long does a customer stay on average?
3. In Example 2, why is the business ₹21,000 worse off and not ₹84,000?

---

**Next:** [6.2 · Money helpers](02-money-helpers.md)

<details><summary>Quiz answers</summary>

1. 10 ÷ 0.04 = ₹250.
2. 1 ÷ (1 − 0.9) = 10 months.
3. The 140 lost orders would have cost money to fulfil too. Only the contribution
   margin (25 %) was profit.

</details>
