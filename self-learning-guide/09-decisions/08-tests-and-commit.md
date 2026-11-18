# 9.8 · Tests and commit

**Time:** 40 minutes · **Before this:** [9.7](07-the-api-and-try-it.md).

## Read

Three test files arrive in this part. One of them is special: `test_isolation.py`
creates **one of every record Bob's organization can own**: a business, a component, a
scenario, a run, an AI analysis, a scan, an alert and a decision. Then it checks that
Alice can't see, list, change, delete or link to **any** of them.

Every part so far had its own "Bob can't see Alice's things" test. This file checks all
the tables in one place, so when you add a new table later, you add one line here and
it's covered.

## Do

### 1. The tests

Make `decisions/tests/` with an **empty** `__init__.py`, then **copy** these three files
from the reference project into it:

- `decisions/tests/test_decision_api.py`
- `decisions/tests/test_workflow_and_brief.py`
- `decisions/tests/test_isolation.py`

### 2. Run them

```bash
pytest
```

### 3. Tidy and commit

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
git commit -m "Part 9: decisions and the brief"
```

## Check

- `pytest` prints `247 passed` (195 before + 52 new).
- `git log --oneline` shows six commits.

**Try breaking it on purpose:** in `decisions/services/brief.py` line 119, change
`if run is not None:` to `if False:`, so the brief always uses **today's** assumptions.
Run `pytest`. `test_brief_uses_the_frozen_snapshot_not_todays_values` fails: after
someone changed daily orders to 9,999, the brief would claim the old decision was based
on 9,999. Put it back.

## What each test proves

### `decisions/tests/test_decision_api.py` (6 tests)

| Lines | Test | Proves |
|---|---|---|
| 8–23 | the `alice_run` fixture | A small finished run with three cases. |
| 26–42 | `test_create_decision_linked_to_run` | A full decision is created as proposed, with the owner's name. |
| 45–50 | `test_decision_without_owner_reports_null_owner_name` | No owner is fine. |
| 53–65 | `test_chosen_strategy_must_exist_in_run` | `pray` is refused, naming the field. |
| 68–74 | `test_run_must_belong_to_the_same_business` | A run from another business is refused. |
| 77–86 | `test_status_moves_through_patch` | A legal move works; `maybe` is a validation error. |
| 89–91 | `test_unauthenticated_requests_get_the_standard_error_shape` | Logged out → the standard error shape. |

### `decisions/tests/test_workflow_and_brief.py` (27 tests)

| Lines | Test | Proves |
|---|---|---|
| 43–47 | `test_new_decision_starts_proposed_with_history` | Proposed, two allowed next steps, one history entry. |
| 50–56 | `test_cannot_create_a_pre_approved_decision` | **Key test.** Nobody can create an "already approved" decision. |
| 59–66 | `test_approval_records_who_and_when_and_the_note` | **Key test.** Sign-off: who, when, and the note in the history. |
| 69–73 | `test_illegal_jump_is_refused_with_the_allowed_options` | proposed → done is refused, naming the allowed moves. |
| 76–88 | `test_done_is_final_and_rejected_can_be_reopened` | Done is final; re-opening clears the sign-off. |
| 91–96 | `test_editing_text_does_not_add_history` | Editing the rationale adds no history. |
| 99–104 | `test_chosen_strategy_checked_on_patch_against_linked_run` | The strategy check also works when editing. |
| 110–129 | `test_brief_uses_the_frozen_snapshot_not_todays_values` | **Key test.** The brief shows 2,400 even after daily orders changed to 9,999. |
| 132–136 | `test_brief_without_a_run_says_so` | No run → no outcomes, assumptions not frozen. |
| 139–158 | `test_brief_page_renders_labelled_ai_and_flagged_numbers` | **Key test.** The page shows the AI label, the flagged `14,550`, `₹21,000` and the chosen column. |
| 161–166 | `test_brief_page_is_org_scoped` | Bob gets 404; logged out goes to login. |
| 172–193 | `test_figure_formats_like_an_indian_finance_team` | 15 tests: every row of lesson 9.5's table, and more. |
| 196–199 | `test_indian_grouping_and_source_tags` | `1,00,000`, `999`, `ILL`, `WHAT-IF`. |

### `decisions/tests/test_isolation.py` (19 tests)

| Lines | Test | Proves |
|---|---|---|
| 18–59 | the `bobs_world` fixture | One of every org-owned record, all Bob's. |
| 73–80 | `test_other_orgs_records_answer_404` | **Key test.** 7 tests: every one of Bob's records is a plain "Not found." for Alice. |
| 83–96 | `test_other_orgs_records_never_appear_in_lists` | 7 tests: every list is empty for Alice. |
| 99–107 | `test_other_orgs_records_cannot_be_changed_or_deleted` | Edits, deletes and acknowledgements fail, and nothing changed. |
| 110–114 | `test_other_orgs_nested_components_answer_404` | Components and assumptions too. |
| 117–133 | `test_cannot_attach_records_to_another_orgs_business` | Can't add a scenario or decision to Bob's business. |
| 136–142 | `test_cannot_link_own_decision_to_another_orgs_run` | Can't link to Bob's run. |
| 145–151 | `test_cannot_assign_decision_to_user_outside_org` | Can't make Bob the owner. |

## If it didn't work

| You see | Fix |
|---|---|
| `NoReverseMatch: Reverse for 'run-detail' not found` | You copied the finished `brief.html`. Use the for-now version (lesson 9.6). |
| `TemplateDoesNotExist: decisions/brief.html` | It goes in `templates/decisions/brief.html`, in the `my-warroom` folder. |
| An isolation test gets `200` instead of `404` | That ViewSet is missing `OrgScopedMixin`. The test name tells you which resource. |

## Quiz

1. Why does `test_isolation.py` build one of **every** record?
2. Why must Bob's records answer 404 and not 403?

---

**Part 9 done! ** AI WarRoom now keeps an honest record of what people decided, why,
and on which numbers, and prints it in a form a reviewer can trust. Next, everything gets
a proper face: [Part 10 · The interface](../10-interface/README.md).

<details><summary>Quiz answers</summary>

1. So a new table can't be forgotten: every org-owned record is checked in one place.
2. A 403 ("forbidden") would tell Alice the record **exists**. A 404 tells her nothing.

</details>
