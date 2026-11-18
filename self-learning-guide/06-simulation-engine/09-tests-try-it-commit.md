# 6.9 · Tests, try it, commit

**Time:** 50 minutes · **Before this:** [6.8](08-connect-to-django.md).

## Read

The engine's tests are special: almost every expected number was **worked out by hand**
first and written in the test's docstring, like your paper in lesson 6.1. If the code
ever disagrees with the pencil, the test fails.

## Do

### 1. Copy the four test files

From the reference project into the same places in `my-warroom`:

- `simulation_engine/tests/test_idea.py`
- `simulation_engine/tests/test_disruption.py`
- `simulation_engine/tests/test_runner.py`
- `simulations/tests/test_run_api.py`

Open each one. Read the docstrings: they're the worked examples.

### 2. Run them

```bash
pytest
```

```bash
pytest -p no:django simulation_engine
```

### 3. Try a real run in the browser

Start the server (`python manage.py runserver`), log in at **http://127.0.0.1:8000/**,
open the console (F12 → Console) and paste the `api()` helper from
[Part 5's `practice/api_helper.js`](../05-business-and-api/practice/api_helper.js)
(lesson 5.7). Then, one line at a time:

**A shop with lesson 6.1's numbers:**

```js
const shop = await api("POST", "/api/v1/businesses/", {mode: "operating", name: "Kirana Express"})
```

```js
await api("PUT", `/api/v1/businesses/${shop.id}/assumptions/`, {assumptions: [{key: "daily_orders", value: "2400"}, {key: "average_order_value", value: "600"}, {key: "contribution_margin", value: "25"}, {key: "primary_gateway_share", value: "100"}, {key: "recapture_rate", value: "30"}]})
```

**Its gateway, and checkout depending on it:**

```js
await api("POST", `/api/v1/businesses/${shop.id}/components/`, {key: "payment-gateway", name: "Payment gateway", kind: "payment", criticality: 5})
```

```js
await api("POST", `/api/v1/businesses/${shop.id}/components/`, {key: "checkout", name: "Checkout", kind: "storefront", depends_on: ["payment-gateway"]})
```

**The question: a 2-hour outage from midnight, orders spread evenly:**

```js
const scenario = await api("POST", "/api/v1/scenarios/", {business: shop.id, template_key: "payment_gateway_outage", name: "Gateway down 2h", parameters: {outage_hours: "2", start_hour: "0", demand_profile: "uniform"}})
```

`missing_inputs` is now an empty list `[]`: it can run.

**Run it:**

```js
const run = await api("POST", `/api/v1/scenarios/${scenario.id}/run/`)
```

→ `201`. Open the printed object: `status: "completed"`, the `input_snapshot`, the
`summary` with its `comparison`, and three `results`. Now just the totals:

```js
run.results.map(r => [r.case_key, r.metrics.total_impact.value])
```

→ `wait 21000.00`, `backup 20420.00`, `queue_retry 10050.00`. Your paper from lesson 6.1,
computed by your own code, saved in your own database.

**A what-if, without saving (double the order value):**

```js
const p = await api("POST", "/api/v1/simulate/preview/", {business: shop.id, template_key: "payment_gateway_outage", parameters: {outage_hours: "2", start_hour: "0", demand_profile: "uniform"}, assumptions: {average_order_value: "1200"}})
```

→ `200` with `saved: false`. `p.cases[0].metrics.lost_revenue.value` is `"168000.00"`
(140 lost orders × ₹1,200). Then:

```js
await api("GET", `/api/v1/runs/?business=${shop.id}`)
```

Still only **one** run: the preview saved nothing.

**A run that can't happen:**

```js
const flood = await api("POST", "/api/v1/scenarios/", {business: shop.id, template_key: "warehouse_shutdown", name: "Flood"})
```

```js
await api("POST", `/api/v1/scenarios/${flood.id}/run/`)
```

→ `422`, code `simulation_input_error`, message `Missing assumptions: hourly_capacity,
main_warehouse_share, cancel_rate_per_delay_hour, max_cancel_rate.` List the runs again:
there's a second one now, with `status: "failed"` and that reason. Stop the server.

### 4. Tidy and commit

```bash
ruff format .
```

```bash
ruff check .
```

```bash
git add -A
```

```bash
git commit -m "Part 6: simulation engine"
```

## Check

- `pytest` prints `104 passed` (52 before + 52 new).
- `pytest -p no:django simulation_engine` prints `56 passed, 1 warning`: the whole
  engine, tested without Django.
- The browser run gives 21000.00 / 20420.00 / 10050.00.
- `git log --oneline` shows three commits.

**Try breaking it on purpose:** in `simulation_engine/disruption.py` line 131, change
`recovered = retried + (failed - retried) * recapture` to `recovered = retried`. Run
`pytest -p no:django simulation_engine`. `test_payment_queue_retry_by_hand` fails: it
expected 137 recovered orders and got 110, because the 27 customers who come back on
their own were forgotten. Put it back.

## What each test proves

### `simulation_engine/tests/test_idea.py` (14 tests)

| Lines | Test | Proves |
|---|---|---|
| 41–52 | `test_first_three_months_by_hand` | Months 1–3 match lesson 6.1's table, to the rupee. |
| 55–65 | `test_unit_economics_by_hand` | CAC 500, LTV 2,000, LTV/CAC 4, levelling off at 1,000 orders. |
| 68–77 | `test_first_profitable_month_by_hand` | Month 6 still loses ₹2,428.80; month 7 makes ₹8,056.96. |
| 80–85 | `test_lowest_cash_and_funding_gap` | Cash is lowest in month 6, and ₹10 lakh is enough. |
| 88–92 | `test_funding_gap_when_investment_is_too_small` | With only ₹1 lakh, cash runs out in month 1. |
| 95–101 | `test_zero_conversion_means_no_customers_not_a_crash` | 0 % conversion: no orders, no CAC, no crash. |
| 104–108 | `test_full_retention_has_no_lifetime_value` | 100 % retention: LTV isn't shown (it would be endless). |
| 111–116 | `test_funnel_check_compares_estimate_with_model` | 1,000 expected vs 737.86 modelled: 26.21 % above. |
| 119–126 | `test_cases_apply_their_shocks` | Worst case: 1.4 % conversion, ₹345 cost, 70 % retention. Best never goes above 100 %. |
| 129–134 | `test_worst_case_is_worse_than_expected_which_is_worse_than_best` | The cases are in a sensible order. |
| 137–143 | `test_sensitivity_is_sorted_by_swing_and_symmetric_inputs_move_cash_both_ways` | Biggest swing first; price ±10 % is 450 and 550. |
| 146–148 | `test_same_inputs_same_output` | 3 tests: the same inputs always give the same months. |

### `simulation_engine/tests/test_disruption.py` (22 tests)

| Lines | Test | Proves |
|---|---|---|
| 56–60 | `test_outage_and_backup_fractions_handle_part_hours` | Half-hours are handled (lesson 6.5's example). |
| 66–79 | `test_payment_wait_by_hand` | Lesson 6.1: 200 affected, 140 lost, ₹21,000. |
| 82–84 | `test_affected_value_is_not_lost_revenue_is_not_lost_profit` | Affected value > lost revenue > lost contribution. |
| 87–103 | `test_payment_backup_by_hand` | Backup: 90 via backup, total impact ₹17,630. |
| 106–118 | `test_payment_queue_retry_by_hand` | Lesson 6.1: 137 recovered, ₹10,050. |
| 121–124 | `test_retry_window_excludes_payments_that_waited_too_long` | Payments older than the window aren't retried. |
| 127–131 | `test_backup_that_switches_after_the_outage_does_nothing_and_costs_nothing` | A too-slow backup costs nothing and changes nothing. |
| 134–137 | `test_backup_never_recovers_more_than_its_capacity` | Capacity is a real limit. |
| 140–145 | `test_zero_outage_means_zero_impact` | 3 tests: no outage, no impact, for each strategy. |
| 148–152 | `test_zero_orders_does_not_divide_by_zero` | A shop with no orders doesn't crash. |
| 155–158 | `test_recovered_plus_lost_equals_affected` | 3 tests: no order disappears from the sums. |
| 164–169 | `test_cancellation_grows_per_hour_and_caps` | 0 %, 4 %, capped at 30 %; notice brings 4 % down to 1.8 %. |
| 172–192 | `test_warehouse_wait_by_hand` | Lesson 6.6's table: 294 delayed, 7.88 lost, back after 4 hours. |
| 195–209 | `test_warehouse_queue_and_notify_by_hand` | The same with notice: 3.58 lost, ₹1,428.26 in total. |
| 212–217 | `test_warehouse_backup_reduces_cancellations_and_charges_for_itself` | Backup helps, and its cost is counted. |
| 220–230 | `test_capacity_shortfall_without_outage_is_not_blamed_on_the_outage` | A normal-day backlog isn't blamed on the outage. |
| 233–242 | `test_backlog_not_cleared_in_horizon_reports_no_recovery_time` | Never recovered in the period → no recovery time, not a made-up one. |
| 245–250 | `test_timeline_has_one_row_per_hour_and_running_impact_matches_total` | 24 rows; the running total ends at the total impact. |

### `simulation_engine/tests/test_runner.py` (8 tests)

| Lines | Test | Proves |
|---|---|---|
| 39–47 | `test_idea_run_returns_seven_cases_and_sensitivity` | Seven cases in order, 8 sensitivity rows, the worst case says what it assumed. |
| 50–52 | `test_idea_warns_when_estimate_far_exceeds_funnel` | Expecting 3,000 orders triggers the funnel warning. |
| 55–58 | `test_missing_assumptions_are_named` | A missing number is named in the error. |
| 61–73 | `test_payment_run_compares_three_strategies_without_picking_a_winner` | The comparison names extremes; waiting is cheapest up front but not overall. |
| 76–84 | `test_component_health_propagates_one_hop_only` | Gateway at 0, checkout at 0.3, revenue untouched. |
| 87–90 | `test_missing_component_falls_back_to_generic_node_with_warning` | No warehouse component → a generic node and a warning. |
| 93–97 | `test_late_backup_warning` | A backup slower than the outage gets a warning. |
| 100–103 | `test_runs_are_reproducible` | Two runs, identical results. |

### `simulations/tests/test_run_api.py` (8 tests)

| Lines | Test | Proves |
|---|---|---|
| 51–62 | `test_run_saves_snapshot_and_one_result_per_strategy` | 201, three results, ₹21,000, the snapshot, the failed component, checkout's health. |
| 65–73 | `test_editing_the_business_never_changes_a_past_run` | **Key test.** Doubling daily orders changes the **next** run, never the old one. |
| 76–80 | `test_identical_inputs_give_identical_hash` | Same inputs, same fingerprint; still two separate runs. |
| 83–93 | `test_missing_inputs_return_422_and_record_a_failed_run` | 422 naming the number, and a failed run is saved. |
| 96–111 | `test_preview_answers_without_saving` | A what-if price gives ₹1,68,000 lost revenue and saves nothing. |
| 114–122 | `test_preview_rejects_out_of_range_slider_values` | A 180 % margin from a slider → 422 naming the field. |
| 125–131 | `test_preview_and_run_are_scoped_to_the_users_org` | **Key test.** Bob's business and scenario are 404 for Alice. |
| 134–151 | `test_idea_run_includes_sensitivity_and_funnel_check` | A full idea run through the API: 7 results, profitable in month 7, funnel gap 26.21 %. |

## If it didn't work

| You see | Fix |
|---|---|
| A `..._by_hand` test fails | Compare the file named in the error with the reference, around the lines the lesson for that file explains. The docstring of the test tells you the right numbers. |
| `fixture 'bob_shop' not found` | `conftest.py` must be the full file from lesson 4.9. |
| `403` with *"CSRF Failed"* in the console | Reload the page (F5) and paste the helper again. |
| `422` on the gateway run | `missing_inputs` wasn't empty: check the assumptions PUT returned `200`. |

## Quiz

1. Why are the expected numbers in the engine tests written in docstrings?
2. Which test proves that history can't be rewritten?
3. You run the same scenario twice without changing anything. Same `input_hash`? Same
   `id`?

---

**Part 6 done! ** AI WarRoom can now answer its "what if?" questions with numbers you
can check by hand, and keep every answer as a permanent record. Next, an AI explains
those numbers in plain words, without being allowed to invent any:
[Part 7 · AI with Gemini](../07-ai-with-gemini/README.md).

<details><summary>Quiz answers</summary>

1. So a person can check the maths on paper, and see exactly what the code must produce.
2. `test_editing_the_business_never_changes_a_past_run`.
3. The same hash (same inputs), but a different id: each run is its own record.

</details>
