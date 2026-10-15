# Testing

## Run everything

```bash
# with the venv active and the database built
python -m pytest tests -q
```

Tests that need PostgreSQL or FastAPI **skip themselves** when those aren't available, so the suite
always runs. Without pytest, each file also runs on its own, for example `python tests/test_backend.py`.

In VS Code, use the **Testing** panel (flask icon) or `Ctrl+Shift+P` → **Tasks: Run Task** →
**Tests: run all**.

## What is tested

| File | Tests | Covers | Needs |
|---|---:|---|---|
| `tests/test_dataset.py` | 11 | Row counts, primary and foreign keys, headcount, SLA rule coverage, calendar coverage, controlled DQ levels, injection log, built-in patterns, manifest hashes | Python only |
| `tests/test_database.py` | 7 | Fact row count = business rules; KPIs = independent pandas implementation; read-only role; breach + compliance = 100; Pareto monotonic; no duplicates or negative durations; all 37 analysis queries execute | PostgreSQL |
| `tests/test_analytics.py` | 6 | Wilson interval and Cramér's V against known values; pandas cleaning = SQL fact ticket for ticket; breach-rate definition; **model features exclude post-creation fields**; customer history uses only earlier outcomes | Python only |
| `tests/test_backend.py` | 15 | Filter parsing and validation; parameterised WHERE (no values in SQL text); previous-period maths; page and sort whitelists; LIKE escaping; **every endpoint's SQL against the real database** (KPIs reconcile, filters partition the data, Pareto ends at 100, team sums = total, pagination, search, **SQL injection attempt**, status filter, meta) | PostgreSQL for 10 of 15 |
| `tests/test_api.py` | 25 (parametrised) | HTTP level via FastAPI `TestClient`: health, meta, every endpoint returns 200, filters echoed, previous period, **422 for 11 kinds of bad input**, pagination consistency, CORS header, 404 | FastAPI + PostgreSQL |
| `database/checks.sql` | 15 | Staging → clean → fact reconciliation, label standardisation, no negative durations in KPIs, targets present, Pareto 100%, FCR consistency, CSAT range, every DQ flag audited | Runs in every database build |
| `scripts/reconcile_db.py` | 82 comparisons | SQL vs pandas: overall KPIs, per team, per month | PostgreSQL |
| `scripts/validate_dataset.py` | 67 checks | Raw extract: structural (blocking) and data quality (reported), with a detection rate per injected issue | Python only |

Results when the project was built: data 11/11, database 7/7, analytics 6/6, backend 15/15,
database checks 15/15, reconciliation 82/82. `test_api.py` could not run in the build environment
because FastAPI couldn't be installed there; run it on your machine.

## Manual UI checks (React dashboard)

Start the API and the dashboard (README → *Run the full application*), then check each item:

- [ ] Overview loads with the last six months; the headline sentence and 8 KPIs show changes vs the previous period
- [ ] Changing the period preset or dates updates every chart, and the URL changes
- [ ] Copying the URL into a new tab reproduces the same view
- [ ] Priority, Team, Category and Region multi-selects filter the data; Reset clears them
- [ ] Every chart's **Table** button shows the same numbers as a table
- [ ] Customers: search narrows the table; sorting a column re-orders it server-side; paging works; "At risk" badges show
- [ ] Tickets: the status tabs filter; searching for a ticket ID finds it
- [ ] Stop the API and refresh: each page shows "Couldn't load this view…" with **Try again**
- [ ] Choose filters with no data (for example P1 + Database + Wales): the empty state appears and nothing crashes
- [ ] Keyboard only: Tab reaches every control, focus is visible, Esc closes the filter menus
- [ ] Narrow window (375 px): the menu button opens the navigation drawer, nothing scrolls sideways
- [ ] `npm run build` completes with no TypeScript errors

## Performance (NFR-01)

```bash
python scripts/load_test.py --requests 50 --concurrency 5
```

This prints p50, p95 and max per endpoint, and PASS if the worst p95 is under 1,000 ms.

## Regenerating every analysis output

```bash
bash scripts/run_all_analysis.sh        # Windows: scripts\run_all_analysis.ps1
```
