# Part 9 · Decisions and the brief

**Time:** about 3 hours · **Before this:** [Part 8](../08-websites-safely/README.md)
(your `my-warroom` passes 194 tests).

So far AI WarRoom calculates (Part 6), explains (Part 7) and reads websites (Part 8). None
of that **decides** anything. In this part a **person** records a decision:

> **Decision:** Queue and retry payments during outages.
> **Owner:** Priya. **Why:** lowest total impact in the model, cheap to set up.
> **Status:** proposed → approved (by Priya, 15 Nov, "Agreed with the ops lead").

Then the app prints a **decision brief**: one page with everything a reviewer needs. What
was tested, which assumptions, the numbers for every option, the AI's reading (clearly
labelled), the committee, the full history, and what the brief is **not**.

Three rules run through this part:

| Rule | How the code keeps it |
|---|---|
| Only people decide | No AI code ever creates, approves or rejects a decision |
| Every change leaves a trace | Each status change is added to a history list: who, when, from, to, why |
| The brief never recalculates | It's built only from saved data, so it shows what the decision was **really** based on, even if the business changes later |

## Lessons in this part (do them in order)

| # | Lesson | You will build |
|---|---|---|
| 9.1 | [Humans decide](01-humans-decide.md) | (Reading only) why decisions are records, and the status map |
| 9.2 | [The Decision table](02-the-decision-table.md) | `decisions/models.py` and the admin |
| 9.3 | [The workflow](03-the-workflow.md) | `workflow.py`: which status can follow which |
| 9.4 | [The brief](04-the-brief.md) | `brief.py`: one dictionary with everything |
| 9.5 | [Numbers the Indian way](05-numbers-the-indian-way.md) | Template filters: `₹1,23,45,678` |
| 9.6 | [The printable page](06-the-printable-page.md) | The brief page and its sign-off buttons |
| 9.7 | [The API, and try it](07-the-api-and-try-it.md) | `decisions/api.py`; record, approve and print a decision |
| 9.8 | [Tests and commit](08-tests-and-commit.md) | 52 new tests, including one for every org-owned record |

When you finish, go to [Part 10 · The interface](../10-interface/README.md).
