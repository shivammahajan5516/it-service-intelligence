# Career portfolio material (Phase 11)

> Present this honestly: it is a **personal portfolio project** using **synthetic data** about a
> **fictional** company. Don't describe Northbridge as a client or employer. The strongest framing is
> "I designed a realistic scenario, generated data with known patterns, and built and tested the full
> analytics pipeline end to end."

## 1. GitHub README

The project's `README.md` is written as the GitHub landing page. Before publishing:
1. Add 4–6 screenshots (`docs/screenshots_checklist.md`).
2. Fill in your name and LinkedIn URL at the bottom.
3. Add repository topics: `data-analysis`, `business-analysis`, `sql`, `postgresql`, `python`,
   `fastapi`, `react`, `power-bi`.

## 2. LinkedIn project description

**Title:** IT Service Intelligence Platform: SLA monitoring and root-cause analysis (portfolio project)

> I built an end-to-end analytics platform for a fictional UK managed IT services provider, to
> practise the full Data Analyst and Business Analyst workflow on a realistic service-desk problem.
>
> • **Business analysis:** defined 10 problem statements, measurable objectives, a stakeholder map,
> a KPI catalogue, business rules, As-Is/To-Be processes and 13 user stories with Given/When/Then
> acceptance criteria.
> • **Data:** generated 22,000 reproducible synthetic tickets with controlled data-quality issues,
> then validated them with 67 checks that caught 99.8% of the injected problems.
> • **SQL:** built a PostgreSQL pipeline (staging → clean → analytics) with 44 constraints and an
> audit trail, and wrote 37 analytical queries (CTEs, window functions, percentiles, Pareto,
> standardisation), each executed and interpreted.
> • **Python:** cleaning, statistical testing (chi-square, Mann–Whitney, Kruskal–Wallis,
> Mantel–Haenszel), k-means segmentation, and an SLA-breach risk model on a chronological split
> (ROC-AUC 0.85 against 0.59 for a rule baseline).
> • **Full stack:** FastAPI REST API (parameterised SQL, read-only role) and a React + TypeScript
> dashboard with five analysis views, plus a Power BI star schema with 40 DAX measures.
> • **Quality:** SQL KPIs reconciled against an independent pandas implementation (82/82 checks), and
> automated tests across the stack.
>
> The analysis found that breaches tracked workload, fell hardest on Platinum customers because of
> tighter targets, and were concentrated in three teams. It led to 11 prioritised recommendations.
> All data is synthetic.
>
> Skills: SQL · PostgreSQL · Python · pandas · scikit-learn · Power BI · DAX · FastAPI · React ·
> TypeScript · Requirements analysis · KPI design · Root cause analysis

## 3. CV bullet points (projects section)

**IT Service Intelligence Platform** (personal project, synthetic data) | SQL, Python, Power BI, FastAPI, React

- Designed and built an end-to-end service-desk analytics platform over 22,000 synthetic tickets:
  a PostgreSQL staging → clean → analytics pipeline with 44 integrity constraints and an audit trail
  of every data-quality correction. KPIs were reconciled to within rounding against an independent
  Python implementation (82/82 checks).
- Wrote 37 analytical SQL queries and a Python statistical analysis (window functions, Pareto,
  indirect standardisation, chi-square and Mantel–Haenszel tests, k-means segmentation). They showed
  that SLA breaches tracked team workload (r = 0.71) and fell hardest on Platinum contracts (33% vs
  4%), and led to 11 prioritised recommendations with owners and KPIs.
- Produced a full BA pack (stakeholder map, KPI catalogue, business rules, As-Is/To-Be processes,
  13 user stories with Given/When/Then criteria), delivered as a FastAPI + React dashboard and a
  Power BI star schema with 40 DAX measures. Added a breach-risk model on a chronological split
  (ROC-AUC 0.85 vs 0.59 baseline).

*(Pick two or three bullets depending on the role: lead with the BA bullet for BA roles and the SQL
bullet for DA roles.)*

## 4. Two-minute interview explanation

> "I wanted a portfolio project that reflects the work I've done around client issues and support
> teams, so I set up a realistic scenario: a fictional UK managed IT services company whose SLA
> breaches were rising.
>
> I started as a Business Analyst. I turned management's concerns into ten measurable problem
> statements, mapped the stakeholders (Head of Operations, Service Delivery Manager, team leads,
> customer success), and agreed a KPI catalogue and business rules. For example: what counts as a
> breach, how duplicates are handled, and what a repeat incident is.
>
> I then generated 22,000 synthetic tickets with a fixed seed, deliberately injected data-quality
> problems such as duplicates, bad timestamps and inconsistent labels, and wrote validation that
> caught 99.8% of them. I loaded everything into PostgreSQL through staging, clean and analytics
> layers, so every KPI is defined once and every correction is audited. To prove the definitions
> were right, I implemented them a second time in pandas and reconciled 82 numbers to within
> rounding.
>
> The analysis showed the breach rate rising from about 15% to over 21% as volume grew on flat
> headcount, with three specialist teams responsible for 70% of breaches. One finding I like is that
> Platinum customers breached 33% of the time against 4% for Bronze: not because their tickets were
> handled more slowly, but because queues weren't ordered by contract tightness. I also ran a
> negative control on region, which I'd deliberately given no effect, and the method correctly
> found none.
>
> Finally, I built a FastAPI service and a React dashboard for the stakeholders, plus a Power BI
> model with the same numbers, and wrote eleven recommendations, starting with SLA-aware queue
> ordering and a pre-breach alert, each with an owner and a measurable target."

## 5. Fifteen technical interview questions and answers

**1. Why staging, clean and analytics layers instead of one table?**
Staging keeps the data exactly as received (all text, nothing rejected), so a bad value never stops
a load and can always be traced back. Clean applies types, standardisation and data-quality flags,
logging every change in an audit table. Analytics holds the business rules as views, so the API,
Power BI and the SQL analysis all read one definition of each KPI.

**2. How did you define and calculate the SLA breach rate?**
A ticket breaches if resolution time (resolved_at − created_at, in elapsed hours) exceeds the target
for its customer's SLA level and priority. The denominator is resolved or closed tickets with valid
timestamps and a known target. Open, cancelled, duplicate and invalid-timestamp tickets are excluded.
In SQL, `sla_breached` is NULL outside the population, so `AVG(sla_breached::int)` uses the right
denominator automatically.

**3. How did you handle duplicates?**
Exact duplicate rows were collapsed, and the count was kept in `source_row_count`. Near-duplicates
(same customer, subcategory and priority within 15 minutes) were found with `LAG()` over a partition
and flagged, not deleted, then excluded from KPIs. The validator found 130 of the 132 injected near
duplicates. The two misses had a blank subcategory, which the rule cannot match on.

**4. Why use the median for resolution time?**
Resolution times are log-normal: raw skewness was 2.3–4.7. The mean sits 20–60% above the median and
moves a lot with a few extreme tickets. Removing 83 outliers moved the mean by 17% but the median by
under 1%.

**5. How did you treat outliers?**
I compared three methods: a Tukey fence on log hours, |z| > 3, and a business rule (more than 30
days or more than 10× target). I used the business rule because it has a meaning: a ticket left
open by mistake. These outliers still count as breaches, since the customer did wait, but they are
excluded from average resolution time.

**6. Explain a window function you used.**
For repeat incidents: `created_at − LAG(created_at) OVER (PARTITION BY customer_id, subcategory_id
ORDER BY created_at) <= interval '30 days'`. I also used running totals (`SUM() OVER (PARTITION BY
year ORDER BY month)`), a three-month moving average with a `ROWS BETWEEN 2 PRECEDING` frame, and a
`RANGE` interval frame to detect volume spikes against the previous 28 days.

**7. How did you make sure the SQL numbers were right?**
I wrote the business rules a second time in pandas, directly from the raw CSVs and without reusing
any SQL, then compared 82 KPIs (overall, per team, per month) to within rounding tolerance. The SQL
build also runs 15 assertions, such as "breach + compliance = 100%" and "team totals = overall total".

**8. How did you prevent SQL injection in the API?**
Every value is a psycopg bound parameter, never formatted into SQL. Sort columns come from a
whitelist dictionary. LIKE wildcards in search text are escaped. The API connects as a role that can
only `SELECT` from the analytics schema, in read-only transactions with a statement timeout. A test
sends `'; DROP TABLE …` through the search box and checks that the table still exists.

**9. Your model: how did you avoid target leakage?**
I only used information available when a ticket is logged. Escalation, reopens, first response, root
cause and KB use all happen later, so they were excluded. History features (team load in the
previous 7 days, the customer's prior breach rate) were computed from earlier tickets only, counting
a prior breach only if that ticket had already resolved. A test checks that no post-creation field
is in the feature list.

**10. Why a chronological split, and how did the model perform?**
Random splits leak the future into training, and breach rates were drifting upwards. I trained on
January 2024–March 2025, chose thresholds on April–June 2025, and tested once on July–December 2025.
Logistic regression reached ROC-AUC 0.85 against 0.59 for a business rule, and the top 20% of risk
scores contained 56% of breaches. I chose logistic regression over gradient boosting because their
validation scores were tied and it is easier to explain.

**11. How did you compare teams fairly?**
By indirect standardisation. For each team I compared observed breaches with the breaches expected
if each of its tickets had the company-average rate for its priority and SLA level. Network
Operations' ratio was 1.87, so its raw rate isn't explained by its work mix. End User Computing's
was 0.99, so its higher raw rate is.

**12. What was your negative control?**
I gave region no effect in the data generator, then checked whether my method would wrongly find
one. Raw regional breach rates ranged from 15% to 20%. After standardising for team, priority and
SLA level, every region's ratio was 0.95–1.02. The method didn't produce a false finding.

**13. How does Power BI match the SQL?**
Power BI imports `analytics.pbi_fact_tickets`: the same rows, with 0/1 flags that are blank outside
each population. DAX measures such as `DIVIDE([SLA Breaches], [SLA Population])` mirror the SQL, and
`MEDIAN` and `PERCENTILE.INC` interpolate exactly like `percentile_cont`. I generated an
acceptance-values table independently in pandas for the report to match.

**14. Which statistical tests did you use, and why?**
Chi-square with Cramér's V for team × breach (categorical association). Mann–Whitney U for CSAT met
vs breached (ordinal and skewed). Kruskal–Wallis for resolution time across teams (non-normal). A
Mantel–Haenszel odds ratio for escalation stratified by priority (controls a confounder). Wilson
intervals for small-sample proportions. And linear regression for the trend.

**15. What would you change for a real deployment?**
Connect to the ITSM tool's API for incremental loads. Add business-hours SLA calendars and clock
pausing. Add authentication and role-based access. Calibrate and serve the risk model with drift
monitoring. Schedule refreshes. Add CI that rebuilds the database and runs the tests on every change.

## 6. Ten Business Analyst interview questions and answers

**1. How did you turn vague management concerns into requirements?**
I restated each concern as a measurable question with a baseline. For example, "increasing SLA
breaches" became "What share of resolved tickets miss their resolution target, by priority and
team, and how is it trending?" I then wrote SMART objectives with targets, and business requirements
traced to them.

**2. How did you identify and prioritise stakeholders?**
With a power/interest grid. The Head of Operations and the Service Delivery Manager needed managing
closely: one sponsors the work and the other owns the KPI definitions. Team Leads and Customer
Success Managers needed keeping informed through workshops and UAT. Agents were consulted on data
entry and on how the data would be used.

**3. Two stakeholders disagree on a KPI definition. What do you do?**
I'd make the disagreement concrete by showing both definitions on the real data, then agree an owner
for the definition (the Service Delivery Manager here) and record the decision as a numbered
business rule. An example is whether "Pending Customer" time pauses the SLA clock: I documented the
choice as assumption A-03, with the impact, and logged a change request rather than letting each
report decide for itself.

**4. How do you separate requirements from solutions?**
Requirements say what the business needs to do, such as "compare teams on a consistent set of KPIs".
Implementation decisions say how, such as "a team scorecard API endpoint and a sortable table".
I kept them in separate tables with traceability from requirement to implementation to test.

**5. Give an example of acceptance criteria you wrote.**
For the at-risk customer flag: Given a customer with at least 10 resolved tickets in the last 90
days, when two of the following hold (breach rate ≥ 1.5 × company, repeat rate ≥ 20%, CSAT ≤ 3.5 with
at least 5 responses), then the customer shows an "At risk" badge. And given fewer than 5 survey
responses, the CSAT criterion isn't applied.

**6. What did the As-Is to To-Be analysis change?**
The As-Is process works queues first-in-first-out, with no warning before breaches and with manual
monthly reporting. The To-Be adds risk scoring at logging, queues ordered by time-to-breach, an alert
at 75% of target, problem records for recurring workarounds, mandatory root cause at closure, and
automated daily reporting. Each change links to a finding: for example, 45% of breaches were
near-misses that an alert could recover.

**7. How did you handle data-quality issues as a BA?**
I treated them as business decisions, not just technical clean-up. Each issue got a rule (exclude,
correct, or keep and flag), an owner, and visible reporting. Recommendation R9 fixes the source: make
root cause mandatory at closure, because 891 resolved tickets had none.

**8. How did you make the recommendations actionable?**
Each one has the evidence (query or analysis section), an owner, the KPI that will measure it, an
indicative effect clearly labelled as an overlapping upper bound, and a 30/90/180-day sequence. I
also listed checks against gaming, such as watching the reopen rate when pushing on resolution time.

**9. How did you avoid over-claiming from the data?**
I reported associations as associations. For example, knowledge-base use correlates with first-contact
resolution, but simpler issues are more likely to have articles, so I recommended an A/B pilot
rather than claiming the KB causes FCR. I also ran a negative control, and used sample-size rules
for CSAT.

**10. What risks did you identify, and how would you manage them?**
The top ones: teams disputing definitions (signed-off rules and fair adjusted comparisons); metrics
being used to blame agents (team-level views only); speed targets causing premature closure (pair
resolution time with reopen rate); and survey bias (report response rates). Each risk is in the risk
register with a likelihood, impact, mitigation and owner.

## 7. Five limitations and future improvements

| # | Limitation | Future improvement |
|---|---|---|
| 1 | **Synthetic data with known mechanisms.** Findings are recoveries of designed patterns, and ticket volume per agent is lower than in a real service desk. | Apply the same pipeline to a public ITSM data set or anonymised real data; compare which patterns hold. |
| 2 | **Simplified SLA clock** (elapsed hours, no pausing), which overstates breaches compared with typical contracts. | Add business-hours calendars per contract and "Pending Customer" pause intervals from status history. |
| 3 | **Batch extract only;** no incremental loading or status history. | Incremental ELT from an ITSM API (ServiceNow or Jira), using an event table of status changes for time-in-status analysis. |
| 4 | **The risk model is offline and uncalibrated;** it scores only at creation. | Calibrate on validation, serve it through `/api/breach-risk`, re-score open tickets hourly, and monitor drift. |
| 5 | **No authentication or role-based access** in the prototype, and the accessibility audit is not yet complete. | SSO with roles (Team Lead sees their team), Power BI row-level security, and an axe/Lighthouse audit added to CI. |
