# Part 6 · The simulation engine

**Time:** about 5 hours · **Before this:** [Part 5](../05-business-and-api/README.md)
(your `my-warroom` passes 52 tests).

This is the heart of AI WarRoom: the **maths** that answers the "what if?" questions.

- **"Will my tiffin idea run out of money?"** The engine plays the business forward
  month by month, in seven cases (expected, best, worst...), and finds which single number
  matters most.
- **"What does a 4-hour gateway outage cost us?"** The engine plays the shop forward hour
  by hour, under three responses (wait, switch to a backup, queue and retry), and lays
  them side by side.

The engine is **plain Python** in `simulation_engine/`, next to the catalogue from lesson
5.2. No Django, no database, no AI. That makes it fast (milliseconds), easy to test, and
**honest**: every number it gives can be checked with a pencil. Lesson 6.1 shows you how.

Only the last lesson connects it to Django, so a scenario can be **run** and the run
**saved** with a frozen copy of its inputs.

Every code block is the real project code. Two files get new "for now" versions in
[`for-now/`](for-now/): `simulations/api.py` (now with "run" and "preview", still
without the AI analysis from Part 7) and `config/urls.py` (one new address).

## Lessons in this part (do them in order)

| # | Lesson | You will build |
|---|---|---|
| 6.1 | [The maths on paper](01-the-maths-on-paper.md) | (Pencil only) one idea and one outage, worked out by hand |
| 6.2 | [Money helpers](02-money-helpers.md) | `money.py`: percentages, rounding, one shape for every result |
| 6.3 | [The idea model](03-the-idea-model.md) | `idea.py`: month by month, and the headline numbers |
| 6.4 | [Cases and sensitivity](04-cases-and-sensitivity.md) | `cases.py` and `sensitivity.py`: best/worst, and "which number matters most?" |
| 6.5 | [Outages, part 1: checkout](05-outages-checkout.md) | `disruption.py` first half: time slices and the payment gateway |
| 6.6 | [Outages, part 2: the queue](06-outages-the-queue.md) | `disruption.py` second half: warehouse and courier backlogs |
| 6.7 | [The runner](07-the-runner.md) | `runner.py`: one front door for the whole engine |
| 6.8 | [Connect it to Django](08-connect-to-django.md) | Snapshot, run service, the run and preview API |
| 6.9 | [Tests, try it, commit](09-tests-try-it-commit.md) | 52 new tests (104 in total), a real run in the browser, a commit |

When you finish, go to [Part 7 · AI with Gemini](../07-ai-with-gemini/README.md).
