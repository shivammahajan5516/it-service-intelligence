# SQL analysis - 37 queries executed against the PostgreSQL database

> Synthetic data (Northbridge Managed Services Ltd is fictional). Every result below was produced by running the query against the database built by `database/build_database.*`; nothing is typed in by hand. Regenerate with `python scripts/run_sql_analysis.py`.

- Database: `it_service_intelligence`, queried as the read-only role `itsi_app`
- Source: `analytics` schema only (`fact_tickets` and the KPI / dimension views)
- KPI definitions: `docs/04_kpi_catalogue.md`; population rules: `docs/05_business_rules.md`
- Correlation is not causation: where a query shows an association, the interpretation says so. The causal mechanisms in this synthetic data are listed in `docs/06_synthetic_data_design.md`.

## Contents

| # | Title | File | Technique |
|---|---|---|---|
| [Q01](#q01) | Ticket volume and status mix | `01_basics_filtering.sql` | SELECT, GROUP BY, window SUM() OVER () for percentage of total |
| [Q02](#q02) | Open P1/P2 tickets already past their SLA target | `01_basics_filtering.sql` | WHERE with multiple predicates, JOIN to dimensions, ORDER BY, LIMIT |
| [Q03](#q03) | Channel mix by priority | `01_basics_filtering.sql` | Conditional aggregation (COUNT ... FILTER / CASE WHEN) to pivot rows into columns |
| [Q04](#q04) | SLA breach rate by support team | `02_joins_aggregation.sql` | INNER JOIN fact to team dimension, GROUP BY, AVG of a boolean outcome |
| [Q05](#q05) | Categories breaching above the company average | `02_joins_aggregation.sql` | GROUP BY with HAVING, scalar subquery for the benchmark |
| [Q06](#q06) | Breach rate by contracted SLA level and company size | `02_joins_aggregation.sql` | JOIN to customer dimension, two-level GROUP BY, ORDER BY a CASE expression |
| [Q07](#q07) | Agent experience level vs outcomes | `02_joins_aggregation.sql` | LEFT JOIN to agent dimension (keeps unassigned tickets), conditional aggregation |
| [Q08](#q08) | First-contact resolution by channel | `02_joins_aggregation.sql` | Conditional aggregation with FILTER on two dimensions (channel x KB used) |
| [Q09](#q09) | Teams slower than the company median | `03_ctes_subqueries.sql` | CTE for the benchmark, CROSS JOIN to compare every team against it |
| [Q10](#q10) | Does workload drive breaches? (team-quarter) | `03_ctes_subqueries.sql` | Multiple chained CTEs, date_trunc, then corr() and regr_slope() statistical aggregates |
| [Q11](#q11) | Customers less satisfied than their industry peers | `03_ctes_subqueries.sql` | Correlated subquery referencing the outer row's industry |
| [Q12](#q12) | Customers with both a P1 breach and repeat incidents (last 90 days) | `03_ctes_subqueries.sql` | EXISTS and a correlated count subquery, relative date window from the extract snapshot |
| [Q13](#q13) | Out-of-hours queueing effect | `03_ctes_subqueries.sql` | CTE + CASE to label groups, conditional aggregation, ratio of rates |
| [Q14](#q14) | Top 3 customers by volume within each industry | `04_window_functions.sql` | ROW_NUMBER() OVER (PARTITION BY industry ORDER BY tickets DESC) |
| [Q15](#q15) | Team breach-rate ranking, 2024 vs 2025 | `04_window_functions.sql` | RANK() and DENSE_RANK() partitioned by year, then a self-join to compare years |
| [Q16](#q16) | Month-over-month change in SLA breach rate | `04_window_functions.sql` | LAG() over months for previous-period comparison |
| [Q17](#q17) | How soon does the same problem come back? | `04_window_functions.sql` | LEAD() over customer + subcategory, then percentile_cont on the gap, by category |
| [Q18](#q18) | Running total of tickets and breaches by year | `04_window_functions.sql` | SUM() OVER (PARTITION BY year ORDER BY month) running totals |
| [Q19](#q19) | Three-month moving averages | `04_window_functions.sql` | AVG() OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) |
| [Q20](#q20) | Customer volume quartiles | `04_window_functions.sql` | NTILE(4) to bucket customers into volume quartiles, then aggregate per bucket |
| [Q21](#q21) | When do tickets arrive? (weekday x time band) | `05_time_series.sql` | EXTRACT(isodow / hour), CASE time bands, conditional aggregation into a heatmap grid |
| [Q22](#q22) | Year-over-year by quarter | `05_time_series.sql` | date_part, conditional aggregation by year, YoY growth calculation |
| [Q23](#q23) | Detecting volume spikes (major incidents) | `05_time_series.sql` | Calendar LEFT JOIN (zero-filled days), RANGE window over a 28-day interval, ratio to baseline |
| [Q24](#q24) | Change-related incidents over time | `05_time_series.sql` | date_trunc('quarter'), conditional aggregation, window LAG for quarter-over-quarter change |
| [Q25](#q25) | Resolution-time percentiles by priority | `06_sla_percentiles.sql` | percentile_cont with an array of fractions (P50/P75/P90/P95) in one pass |
| [Q26](#q26) | How badly are SLAs missed? | `06_sla_percentiles.sql` | width_bucket() on the overrun ratio, CASE labels, distribution percentages |
| [Q27](#q27) | First-response SLA by priority and channel | `06_sla_percentiles.sql` | GROUP BY GROUPING SETS for channel detail plus per-priority subtotals in one result |
| [Q28](#q28) | Escalation impact by priority | `06_sla_percentiles.sql` | Conditional aggregation of medians with FILTER, ratio of escalated vs not |
| [Q29](#q29) | Root-cause Pareto with ABC classes | `07_pareto_root_cause.sql` | Cumulative SUM() OVER (ORDER BY count DESC) / total, CASE into A/B/C classes |
| [Q30](#q30) | Which subcategories generate the SLA breaches? | `07_pareto_root_cause.sql` | Pareto on breach COUNT (not rate), cumulative window, filter on the running share |
| [Q31](#q31) | Root cause x priority matrix | `07_pareto_root_cause.sql` | Conditional aggregation pivot producing "count (breach %)" cells |
| [Q32](#q32) | Chronic customer problems (repeat incidents) | `07_pareto_root_cause.sql` | GROUP BY two keys, mode() WITHIN GROUP for the most common root cause, HAVING |
| [Q33](#q33) | At-risk customer list (BR-RULE-14) | `08_customer_team.sql` | Read the rule view, build a human-readable reason with CONCAT_WS and CASE |
| [Q34](#q34) | Team scorecard against the company average | `08_customer_team.sql` | AVG() OVER () across the result set for deltas; RANK() for a league position |
| [Q35](#q35) | Do workarounds come back? | `08_customer_team.sql` | GROUP BY with conditional averages; CSAT split by reopened vs not |
| [Q36](#q36) | Knowledge-base use by team | `08_customer_team.sql` | Conditional aggregation by team and KB flag, difference in FCR rates |
| [Q37](#q37) | Negative control - is region a real driver? | `08_customer_team.sql` | Indirect standardisation - expected breaches from team x priority x SLA-level rates, two models compared |

---

## Q01

### Ticket volume and status mix

**1. Business question.** How many valid tickets are in the extract and what state are they in at the snapshot?

**2. SQL solution** (`database/queries/01_basics_filtering.sql`)

```sql
SELECT ticket_status,
       count(*)                                              AS tickets,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2)    AS pct_of_total
FROM analytics.fact_tickets
GROUP BY ticket_status
ORDER BY tickets DESC;
```

**3. Why this technique.** SELECT, GROUP BY, window SUM() OVER () for percentage of total. A window total avoids a second query or subquery to compute each status's share.

**4. Actual result** - 7 row(s), 48 ms including client round-trip; saved to `database/query_results/Q01.csv`

| ticket_status | tickets | pct_of_total |
|---|---|---|
| Closed | 21479 | 97.23 |
| Cancelled | 277 | 1.25 |
| In Progress | 138 | 0.62 |
| Resolved | 84 | 0.38 |
| Pending Customer | 77 | 0.35 |
| On Hold | 30 | 0.14 |
| New | 5 | 0.02 |

**5. Business interpretation.** 97.2% of the 22,090 valid tickets are Closed. The open backlog at the snapshot is 250 tickets (1.1%): 138 In Progress, 77 Pending Customer, 30 On Hold and 5 New. Cancelled tickets (1.25%) are excluded from every SLA and satisfaction KPI. The backlog is small relative to monthly volume, which is about 700–1,150 tickets, so the open-ticket exception list (Q02) is more useful than the backlog count itself.

---

## Q02

### Open P1/P2 tickets already past their SLA target

**1. Business question.** Which high-priority tickets need escalation right now because they have already breached?

**2. SQL solution** (`database/queries/01_basics_filtering.sql`)

```sql
SELECT f.ticket_id, f.priority, t.team_name, c.customer_name, c.sla_level,
       f.ticket_status, f.sla_target_hours, f.open_age_hours,
       round(f.open_age_hours / f.sla_target_hours, 1)       AS times_over_target
FROM analytics.fact_tickets f
JOIN analytics.dim_team t     ON t.team_id = f.team_id
JOIN analytics.dim_customer c ON c.customer_id = f.customer_id
WHERE f.is_open
  AND f.priority IN ('P1', 'P2')
  AND f.is_open_past_target
ORDER BY times_over_target DESC, f.ticket_id
LIMIT 15;
```

**3. Why this technique.** WHERE with multiple predicates, JOIN to dimensions, ORDER BY, LIMIT. An operational exception list - filtering on the backlog flags defined once in the fact view.

**4. Actual result** - 15 row(s), 45 ms including client round-trip; saved to `database/query_results/Q02.csv`

| ticket_id | priority | team_name | customer_name | sla_level | ticket_status | sla_target_hours | open_age_hours | times_over_target |
|---|---|---|---|---|---|---|---|---|
| TKT-020287 | P1 | Security Operations | Kestrel Legal Group | Gold | In Progress | 4.0 | 1375.3 | 343.8 |
| TKT-020756 | P1 | Identity & Access Management | Derwent Components Ltd | Platinum | Pending Customer | 4.0 | 1069.5 | 267.4 |
| TKT-020889 | P1 | Application Support | Stanmore Labs Group | Platinum | Pending Customer | 4.0 | 997.6 | 249.4 |
| TKT-020376 | P2 | Service Desk | Portland Outlets plc | Platinum | Pending Customer | 8.0 | 1331.1 | 166.4 |
| TKT-020571 | P2 | Database Services | Granite Accountants Group | Platinum | Pending Customer | 8.0 | 1192.2 | 149.0 |
| TKT-021463 | P1 | Infrastructure & Cloud | Tyne Authority | Gold | Pending Customer | 4.0 | 575.1 | 143.8 |
| TKT-021632 | P1 | Identity & Access Management | Kestrel Outlets Ltd | Gold | Pending Customer | 4.0 | 484.9 | 121.2 |
| TKT-020983 | P2 | Security Operations | Lomond Financial Ltd | Platinum | In Progress | 8.0 | 949.3 | 118.7 |
| TKT-021001 | P2 | Service Desk | Oakridge Academy Trust | Platinum | In Progress | 8.0 | 904.1 | 113.0 |
| TKT-020724 | P2 | Service Desk | Marlow Outlets Ltd | Gold | Pending Customer | 12.0 | 1104.8 | 92.1 |
| TKT-021267 | P2 | Service Desk | Northgate Engineering plc | Platinum | In Progress | 8.0 | 732.1 | 91.5 |
| TKT-020797 | P2 | Service Desk | Clifton Wealth Ltd | Gold | In Progress | 12.0 | 1060.6 | 88.4 |
| TKT-021416 | P2 | Network Operations | Osprey Bank plc | Platinum | In Progress | 8.0 | 636.4 | 79.6 |
| TKT-021422 | P2 | Identity & Access Management | Ironbridge Digital plc | Platinum | In Progress | 8.0 | 634.4 | 79.3 |
| TKT-021853 | P1 | Identity & Access Management | Northgate Engineering plc | Platinum | In Progress | 4.0 | 306.0 | 76.5 |

**5. Business interpretation.** Some high-priority tickets have been open for weeks. A P1 Security Operations ticket is 1,375 hours old against a 4-hour target, and 10 of the 15 rows are Platinum customers. Most of these tickets are "Pending Customer" or "In Progress". Because the SLA clock never pauses (assumption A-03), they count as breaches even when the delay is the customer's. **Action:** a weekly ageing review of open P1/P2 tickets owned by the Service Delivery Manager. Where a contract allows it, the business should also decide whether "Pending Customer" time should pause the clock.

---

## Q03

### Channel mix by priority

**1. Business question.** Through which channels do tickets of each priority arrive?

**2. SQL solution** (`database/queries/01_basics_filtering.sql`)

```sql
SELECT COALESCE(channel, '(missing)')                         AS channel,
       count(*) FILTER (WHERE priority = 'P1')                AS p1,
       count(*) FILTER (WHERE priority = 'P2')                AS p2,
       count(*) FILTER (WHERE priority = 'P3')                AS p3,
       count(*) FILTER (WHERE priority = 'P4')                AS p4,
       count(*)                                               AS total,
       round(100.0 * sum(CASE WHEN priority IN ('P1', 'P2') THEN 1 ELSE 0 END) / count(*), 1)
                                                              AS pct_high_priority
FROM analytics.fact_tickets
GROUP BY COALESCE(channel, '(missing)')
ORDER BY total DESC;
```

**3. Why this technique.** Conditional aggregation (COUNT ... FILTER / CASE WHEN) to pivot rows into columns. Produces a compact cross-tab in one pass without a PIVOT operator (which PostgreSQL lacks).

**4. Actual result** - 6 row(s), 71 ms including client round-trip; saved to `database/query_results/Q03.csv`

| channel | p1 | p2 | p3 | p4 | total | pct_high_priority |
|---|---|---|---|---|---|---|
| Portal | 148 | 1008 | 3488 | 2707 | 7351 | 15.7 |
| Email | 85 | 683 | 2387 | 1605 | 4760 | 16.1 |
| Phone | 405 | 552 | 1948 | 1460 | 4365 | 21.9 |
| Chat | 56 | 353 | 1399 | 991 | 2799 | 14.6 |
| Monitoring Alert | 226 | 671 | 1349 | 437 | 2683 | 33.4 |
| (missing) | 7 | 23 | 59 | 43 | 132 | 22.7 |

**5. Business interpretation.** Monitoring alerts carry the highest share of high-priority work: 33% of alerts are P1/P2, compared with about 15% for portal, email and chat. Phone is second at 22%, and it carries the most P1s in absolute terms (405). The portal is the largest channel, but its tickets are mostly low priority. 132 tickets have no channel recorded, which is a data-capture gap to raise with the Service Desk.

---

## Q04

### SLA breach rate by support team

**1. Business question.** Which resolver teams breach SLA most often, and on how many tickets?

**2. SQL solution** (`database/queries/02_joins_aggregation.sql`)

```sql
SELECT t.team_id, t.team_name, t.support_tier,
       count(*) FILTER (WHERE f.in_sla_population)            AS resolved_in_scope,
       count(*) FILTER (WHERE f.sla_breached)                 AS breaches,
       round(100 * avg(f.sla_breached::int), 1)               AS sla_breach_pct
FROM analytics.fact_tickets f
JOIN analytics.dim_team t ON t.team_id = f.team_id
GROUP BY t.team_id, t.team_name, t.support_tier
ORDER BY sla_breach_pct DESC, t.team_id;
```

**3. Why this technique.** INNER JOIN fact to team dimension, GROUP BY, AVG of a boolean outcome. sla_breached is NULL outside the SLA population, so AVG() automatically uses the right denominator.

**4. Actual result** - 8 row(s), 72 ms including client round-trip; saved to `database/query_results/Q04.csv`

| team_id | team_name | support_tier | resolved_in_scope | breaches | sla_breach_pct |
|---|---|---|---|---|---|
| T03 | Network Operations | L2/L3 | 3208 | 1130 | 35.2 |
| T04 | Infrastructure & Cloud | L3 | 3117 | 870 | 27.9 |
| T05 | Application Support | L2/L3 | 2879 | 742 | 25.8 |
| T02 | End User Computing | L2 | 3532 | 571 | 16.2 |
| T06 | Identity & Access Management | L2 | 1808 | 207 | 11.4 |
| T08 | Database Services | L3 | 1086 | 118 | 10.9 |
| T07 | Security Operations | L3 | 1361 | 81 | 6.0 |
| T01 | Service Desk | L1 | 4520 | 185 | 4.1 |

**5. Business interpretation.** Breach rates vary roughly ninefold between teams. Network Operations breaches 35.2% of the time, followed by Infrastructure & Cloud (27.9%) and Application Support (25.8%). The Service Desk breaches 4.1%. The three worst teams account for 2,742 of the 3,904 breaches (70%). The teams do handle different work, so Q09, Q10 and Q34 separate out the effects of complexity and workload.

---

## Q05

### Categories breaching above the company average

**1. Business question.** Which incident categories have a breach rate above the overall rate (minimum 200 tickets)?

**2. SQL solution** (`database/queries/02_joins_aggregation.sql`)

```sql
SELECT f.category,
       count(*) FILTER (WHERE f.in_sla_population)            AS resolved_in_scope,
       round(100 * avg(f.sla_breached::int), 1)               AS sla_breach_pct,
       round(100 * (SELECT avg(sla_breached::int) FROM analytics.fact_tickets), 1) AS company_breach_pct
FROM analytics.fact_tickets f
GROUP BY f.category
HAVING count(*) FILTER (WHERE f.in_sla_population) >= 200
   AND avg(f.sla_breached::int) > (SELECT avg(sla_breached::int) FROM analytics.fact_tickets)
ORDER BY sla_breach_pct DESC;
```

**3. Why this technique.** GROUP BY with HAVING, scalar subquery for the benchmark. HAVING filters on the aggregated rate; the subquery keeps the benchmark in the same statement.

**4. Actual result** - 5 row(s), 118 ms including client round-trip; saved to `database/query_results/Q05.csv`

| category | resolved_in_scope | sla_breach_pct | company_breach_pct |
|---|---|---|---|
| Network | 3208 | 35.2 | 18.1 |
| Cloud Services | 1297 | 30.3 | 18.1 |
| Business Applications | 1728 | 29.6 | 18.1 |
| Infrastructure | 1820 | 26.2 | 18.1 |
| Hardware | 2417 | 19.9 | 18.1 |

**5. Business interpretation.** Five categories breach above the company rate of 18.1%: Network (35.2%), Cloud Services (30.3%), Business Applications (29.6%), Infrastructure (26.2%) and Hardware (19.9%). The first four are the specialist categories handled by the three worst teams in Q04, so category and team effects overlap and should not be read as two separate problems.

---

## Q06

### Breach rate by contracted SLA level and company size

**1. Business question.** Do tighter contracts (Platinum) breach more often than looser ones (Bronze)?

**2. SQL solution** (`database/queries/02_joins_aggregation.sql`)

```sql
SELECT c.sla_level, c.company_size,
       count(*) FILTER (WHERE f.in_sla_population)            AS resolved_in_scope,
       round(100 * avg(f.sla_breached::int), 1)               AS sla_breach_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population))::numeric, 1) AS median_resolution_hours
FROM analytics.fact_tickets f
JOIN analytics.dim_customer c ON c.customer_id = f.customer_id
WHERE NOT c.is_placeholder
GROUP BY c.sla_level, c.company_size
ORDER BY CASE c.sla_level WHEN 'Platinum' THEN 1 WHEN 'Gold' THEN 2 WHEN 'Silver' THEN 3 ELSE 4 END,
         CASE c.company_size WHEN 'Large Enterprise' THEN 1 WHEN 'Enterprise' THEN 2
                             WHEN 'Mid-Market' THEN 3 ELSE 4 END;
```

**3. Why this technique.** JOIN to customer dimension, two-level GROUP BY, ORDER BY a CASE expression. Tests whether tighter targets, not slower work, drive breaches; CASE gives business sort order.

**4. Actual result** - 15 row(s), 101 ms including client round-trip; saved to `database/query_results/Q06.csv`

| sla_level | company_size | resolved_in_scope | sla_breach_pct | median_resolution_hours |
|---|---|---|---|---|
| Platinum | Large Enterprise | 3410 | 33.5 | 15.1 |
| Platinum | Enterprise | 1065 | 31.1 | 13.6 |
| Platinum | Mid-Market | 503 | 33.4 | 13.3 |
| Platinum | SME | 76 | 47.4 | 18.2 |
| Gold | Large Enterprise | 2546 | 22.2 | 15.0 |
| Gold | Enterprise | 2641 | 22.1 | 15.6 |
| Gold | Mid-Market | 1678 | 23.2 | 14.7 |
| Gold | SME | 416 | 18.3 | 15.2 |
| Silver | Large Enterprise | 663 | 6.3 | 13.1 |
| Silver | Enterprise | 2394 | 7.4 | 14.0 |
| Silver | Mid-Market | 2905 | 7.5 | 15.1 |
| Silver | SME | 1281 | 8.0 | 14.2 |
| Bronze | Enterprise | 215 | 3.7 | 14.0 |
| Bronze | Mid-Market | 631 | 3.6 | 16.7 |
| Bronze | SME | 1078 | 3.7 | 15.2 |

**5. Business interpretation.** The tighter the contract, the more often it is breached, even though the work takes about the same time. Median resolution sits between 13 and 18 hours for every SLA level, yet breach rates fall from about 33% (Platinum) to 22% (Gold), 7% (Silver) and 4% (Bronze). The most valuable customers therefore have the worst experience against their contract. The cause is not that their tickets are handled more slowly; the targets are simply stricter. **Implication:** routing should prioritise by SLA level, so Platinum P3s are not queued behind Bronze P3s. Platinum SME (n = 76) is too small a group to read on its own.

---

## Q07

### Agent experience level vs outcomes

**1. Business question.** How do resolution time, escalation and reopen rates differ by agent experience?

**2. SQL solution** (`database/queries/02_joins_aggregation.sql`)

```sql
SELECT COALESCE(a.experience_level, '(unassigned)')       AS experience_level,
       count(*)                                           AS tickets,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population))::numeric, 1) AS median_resolution_hours,
       round(100 * avg(f.escalation_flag::int), 1)        AS escalation_pct,
       round(100 * avg(f.is_reopened::int) FILTER (WHERE f.is_resolved), 1) AS reopen_pct,
       round(100 * avg(f.sla_breached::int), 1)           AS sla_breach_pct
FROM analytics.fact_tickets f
LEFT JOIN analytics.dim_agent a ON a.agent_id = f.agent_id
GROUP BY COALESCE(a.experience_level, '(unassigned)')
ORDER BY median_resolution_hours DESC NULLS LAST;
```

**3. Why this technique.** LEFT JOIN to agent dimension (keeps unassigned tickets), conditional aggregation. A LEFT JOIN makes the unassigned group visible instead of silently dropping it.

**4. Actual result** - 5 row(s), 103 ms including client round-trip; saved to `database/query_results/Q07.csv`

| experience_level | tickets | median_resolution_hours | escalation_pct | reopen_pct | sla_breach_pct |
|---|---|---|---|---|---|
| Junior | 6628 | 20.3 | 22.7 | 9.3 | 18.4 |
| Intermediate | 9169 | 15.6 | 19.2 | 5.8 | 18.1 |
| (unassigned) | 88 | 14.1 | 23.9 | 6.8 | 21.6 |
| Senior | 5028 | 9.9 | 23.5 | 5.9 | 17.1 |
| Lead | 1177 | 9.3 | 26.9 | 8.5 | 21.3 |

**5. Business interpretation.** Junior agents have the slowest median resolution: 20.3 hours, against 9.9 hours for Seniors and 9.3 hours for Leads. They also have the highest reopen rate (9.3%). Their breach rate (18.4%) is no worse than average, though, because Leads and Seniors are assigned more P1/P2 work, and P1/P2 targets are tighter. Leads show the highest escalation rate (26.9%) for the same reason. This is a **confounded comparison**: priority mix differs by experience level. A fair comparison needs to hold priority constant, which is done in the Phase 5 Python analysis.

---

## Q08

### First-contact resolution by channel

**1. Business question.** Which channels give the best first-contact resolution, and how does KB use change it?

**2. SQL solution** (`database/queries/02_joins_aggregation.sql`)

```sql
SELECT channel,
       count(*) FILTER (WHERE in_fcr_population)                         AS fcr_population,
       round(100 * avg(fcr_achieved::int), 1)                            AS fcr_pct,
       round(100 * avg(fcr_achieved::int) FILTER (WHERE knowledge_base_used), 1)     AS fcr_pct_kb_used,
       round(100 * avg(fcr_achieved::int) FILTER (WHERE NOT knowledge_base_used), 1) AS fcr_pct_no_kb
FROM analytics.fact_tickets
WHERE channel IS NOT NULL
GROUP BY channel
ORDER BY fcr_pct DESC;
```

**3. Why this technique.** Conditional aggregation with FILTER on two dimensions (channel x KB used). Shows the FCR rate with and without knowledge-base use side by side for each channel.

**4. Actual result** - 5 row(s), 68 ms including client round-trip; saved to `database/query_results/Q08.csv`

| channel | fcr_population | fcr_pct | fcr_pct_kb_used | fcr_pct_no_kb |
|---|---|---|---|---|
| Chat | 2721 | 34.1 | 52.9 | 19.4 |
| Phone | 4245 | 31.4 | 48.0 | 18.4 |
| Portal | 7151 | 26.6 | 42.8 | 13.0 |
| Email | 4639 | 26.4 | 42.1 | 14.0 |
| Monitoring Alert | 2617 | 0.0 | 0.0 | 0.0 |

**5. Business interpretation.** Chat (34%) and phone (31%) have the best first-contact resolution, ahead of portal and email (about 26%). In every channel, tickets where the knowledge base was used reach roughly 2.5–3.5 times the FCR rate of those where it wasn't (for example, chat 52.9% vs 19.4%). This is an association, not proof that the KB *causes* FCR, because simpler issues are both more likely to have an article and easier to fix first time. Monitoring alerts show 0% by definition: there is no customer contact to resolve at.

---

## Q09

### Teams slower than the company median

**1. Business question.** Which teams' median resolution time exceeds the company-wide median, and by how much?

**2. SQL solution** (`database/queries/03_ctes_subqueries.sql`)

```sql
WITH company AS (
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours) AS median_h
    FROM analytics.fact_tickets WHERE in_duration_population
), team AS (
    SELECT team_id,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours) AS median_h,
           count(*) AS n
    FROM analytics.fact_tickets WHERE in_duration_population
    GROUP BY team_id
)
SELECT d.team_name, t.n AS resolved_tickets,
       round(t.median_h::numeric, 1)                      AS team_median_hours,
       round(c.median_h::numeric, 1)                      AS company_median_hours,
       round((t.median_h / c.median_h)::numeric, 2)       AS ratio_to_company
FROM team t
CROSS JOIN company c
JOIN analytics.dim_team d USING (team_id)
WHERE t.median_h > c.median_h
ORDER BY ratio_to_company DESC;
```

**3. Why this technique.** CTE for the benchmark, CROSS JOIN to compare every team against it. The CTE names the benchmark once; the main query reads like the business question.

**4. Actual result** - 4 row(s), 132 ms including client round-trip; saved to `database/query_results/Q09.csv`

| team_name | resolved_tickets | team_median_hours | company_median_hours | ratio_to_company |
|---|---|---|---|---|
| Network Operations | 3196 | 29.7 | 14.8 | 2.0 |
| Infrastructure & Cloud | 3106 | 21.8 | 14.8 | 1.47 |
| End User Computing | 3521 | 19.5 | 14.8 | 1.31 |
| Application Support | 2870 | 18.3 | 14.8 | 1.23 |

**5. Business interpretation.** Four teams are slower than the company median of 14.8 hours. Network Operations is 2.0 times slower (29.7 hours), followed by Infrastructure & Cloud (1.47×), End User Computing (1.31×) and Application Support (1.23×). End User Computing is notable because it handles mostly Low/Medium-complexity hardware and software work, yet is still 31% slower than average. That points to capacity rather than complexity, which Q10 tests.

---

## Q10

### Does workload drive breaches? (team-quarter)

**1. Business question.** Across team-quarters, is a higher ticket load per agent associated with a higher breach rate?

**2. SQL solution** (`database/queries/03_ctes_subqueries.sql`)

```sql
WITH team_quarter AS (
    SELECT team_id, date_trunc('quarter', created_at)::date AS quarter,
           count(*)                       AS tickets,
           avg(sla_breached::int)         AS breach_rate
    FROM analytics.fact_tickets
    GROUP BY team_id, date_trunc('quarter', created_at)
), loaded AS (
    SELECT q.*, q.tickets / 3.0 / t.planned_headcount AS tickets_per_agent_month
    FROM team_quarter q
    JOIN analytics.dim_team t USING (team_id)
), summary AS (
    SELECT count(*)                                                  AS team_quarters,
           round(corr(tickets_per_agent_month, breach_rate)::numeric, 3) AS pearson_r,
           round((100 * regr_slope(breach_rate, tickets_per_agent_month))::numeric, 2)
                                                                     AS breach_pp_per_extra_ticket
    FROM loaded
)
SELECT 'All team-quarters' AS scope, * FROM summary
UNION ALL
SELECT 'Excluding Service Desk (T01)', count(*),
       round(corr(tickets_per_agent_month, breach_rate)::numeric, 3),
       round((100 * regr_slope(breach_rate, tickets_per_agent_month))::numeric, 2)
FROM loaded WHERE team_id <> 'T01';
```

**3. Why this technique.** Multiple chained CTEs, date_trunc, then corr() and regr_slope() statistical aggregates. Builds the analysis grain step by step; corr() gives a single association measure in SQL.

**4. Actual result** - 2 row(s), 72 ms including client round-trip; saved to `database/query_results/Q10.csv`

| scope | team_quarters | pearson_r | breach_pp_per_extra_ticket |
|---|---|---|---|
| All team-quarters | 64 | 0.709 | 1.86 |
| Excluding Service Desk (T01) | 56 | 0.755 | 1.79 |

**5. Business interpretation.** Across 64 team-quarters, tickets per agent per month correlates strongly with breach rate (Pearson r = 0.71). Each additional ticket per agent per month is associated with about 1.9 percentage points more breaches. The relationship holds when the Service Desk is excluded (r = 0.76), so it is not driven by that one large, low-breach team. Workload is still confounded with team complexity, so this is evidence for, not proof of, a capacity problem. It does support **rebalancing headcount towards Network Operations and End User Computing**, which carry the highest load per agent.

---

## Q11

### Customers less satisfied than their industry peers

**1. Business question.** Which customers (>= 10 survey responses) have average CSAT at least 0.5 below their industry average?

**2. SQL solution** (`database/queries/03_ctes_subqueries.sql`)

```sql
SELECT cs.customer_name, cs.industry, cs.csat_responses, cs.avg_csat,
       round((SELECT avg(f.customer_satisfaction)
              FROM analytics.fact_tickets f
              JOIN analytics.dim_customer c2 ON c2.customer_id = f.customer_id
              WHERE c2.industry = cs.industry), 2)          AS industry_avg_csat
FROM analytics.customer_summary cs
WHERE cs.csat_responses >= 10
  AND cs.avg_csat <= (SELECT avg(f.customer_satisfaction)
                      FROM analytics.fact_tickets f
                      JOIN analytics.dim_customer c2 ON c2.customer_id = f.customer_id
                      WHERE c2.industry = cs.industry) - 0.5
ORDER BY cs.avg_csat, cs.csat_responses DESC, cs.customer_name
LIMIT 15;
```

**3. Why this technique.** Correlated subquery referencing the outer row's industry. The benchmark differs per row (per industry), which is what a correlated subquery expresses.

**4. Actual result** - 15 row(s), 441 ms including client round-trip; saved to `database/query_results/Q11.csv`

| customer_name | industry | csat_responses | avg_csat | industry_avg_csat |
|---|---|---|---|---|
| Pennine Industries Group | Manufacturing | 14 | 2.79 | 4.02 |
| Foxley Water Ltd | Energy & Utilities | 13 | 3.0 | 3.81 |
| Heron Authority | Public Sector | 13 | 3.0 | 3.96 |
| Pembroke Outlets plc | Retail | 12 | 3.0 | 3.98 |
| Brightwater Advisory plc | Professional Services | 44 | 3.09 | 3.94 |
| Granite Power Ltd | Energy & Utilities | 12 | 3.17 | 3.81 |
| Clifton Clinics Ltd | Healthcare | 57 | 3.23 | 3.94 |
| Larkfield Pharma Ltd | Healthcare | 32 | 3.25 | 3.94 |
| Oakridge Academy Trust | Education | 31 | 3.26 | 3.89 |
| Cotswold Technologies Ltd | Technology | 23 | 3.26 | 4.08 |
| Marlow Insurance plc | Financial Services | 19 | 3.26 | 3.94 |
| Ullswater Council | Public Sector | 13 | 3.31 | 3.96 |
| Greystone Labs Group | Technology | 15 | 3.33 | 4.08 |
| Elmstead Legal Ltd | Professional Services | 17 | 3.35 | 3.94 |
| Granite Digital Ltd | Technology | 11 | 3.36 | 4.08 |

**5. Business interpretation.** Fifteen customers with at least 10 survey responses score at least 0.5 below their industry average. Pennine Industries Group has the lowest score (2.79 against a manufacturing average of 4.02). Clifton Clinics Ltd (57 responses, 3.23) and Brightwater Advisory plc (44 responses, 3.09) have large samples, so their low scores are reliable signals rather than noise. These customers belong on the Customer Success Manager review list. Clifton Clinics is also flagged by the formal at-risk rule (Q33).

---

## Q12

### Customers with both a P1 breach and repeat incidents (last 90 days)

**1. Business question.** Which customers had a breached P1 AND at least three repeat incidents in the final 90 days?

**2. SQL solution** (`database/queries/03_ctes_subqueries.sql`)

```sql
SELECT c.customer_id, c.customer_name, c.sla_level, c.customer_success_manager,
       (SELECT count(*) FROM analytics.fact_tickets r
        WHERE r.customer_id = c.customer_id AND r.is_repeat_incident
          AND r.created_at > (SELECT snapshot_at FROM analytics.extract) - interval '90 days') AS repeat_incidents_90d
FROM analytics.dim_customer c
WHERE EXISTS (SELECT 1 FROM analytics.fact_tickets f
              WHERE f.customer_id = c.customer_id AND f.priority = 'P1' AND f.sla_breached
                AND f.created_at > (SELECT snapshot_at FROM analytics.extract) - interval '90 days')
  AND (SELECT count(*) FROM analytics.fact_tickets r
       WHERE r.customer_id = c.customer_id AND r.is_repeat_incident
         AND r.created_at > (SELECT snapshot_at FROM analytics.extract) - interval '90 days') >= 3
ORDER BY repeat_incidents_90d DESC, c.customer_name;
```

**3. Why this technique.** EXISTS and a correlated count subquery, relative date window from the extract snapshot. EXISTS stops at the first match and states "at least one" intent clearly.

**4. Actual result** - 17 row(s), 50 ms including client round-trip; saved to `database/query_results/Q12.csv`

| customer_id | customer_name | sla_level | customer_success_manager | repeat_incidents_90d |
|---|---|---|---|---|
| CUST-0455 | Granite Renewables plc | Platinum | Daniel Price | 13 |
| CUST-0130 | Abbey Software Ltd | Gold | Hannah Lloyd | 11 |
| CUST-0388 | Ironbridge Bank plc | Gold | Hannah Lloyd | 9 |
| CUST-0407 | Riverside Stores Ltd | Platinum | Isla Murray | 8 |
| CUST-0475 | Cotswold Components Ltd | Platinum | Isla Murray | 7 |
| CUST-0002 | Northgate Engineering plc | Platinum | Priya Kaur | 7 |
| CUST-0015 | Albion Home Ltd | Gold | Daniel Price | 6 |
| CUST-0400 | Derwent Components Ltd | Platinum | Daniel Price | 6 |
| CUST-0229 | Holloway Distribution Ltd | Gold | Priya Kaur | 6 |
| CUST-0034 | Yarrow Advisory LLP | Gold | Isla Murray | 6 |
| CUST-0326 | Stanmore Labs Group | Platinum | Priya Kaur | 5 |
| CUST-0146 | Foxley Logistics Ltd | Platinum | Daniel Price | 4 |
| CUST-0391 | Bramley Legal Ltd | Platinum | Priya Kaur | 3 |
| CUST-0463 | Granite Accountants Group | Platinum | Kofi Mensah | 3 |
| CUST-0323 | Linden Accountants Ltd | Gold | Daniel Price | 3 |
| CUST-0245 | Nevis Manufacturing Ltd | Platinum | Isla Murray | 3 |
| CUST-0209 | Vale Health Ltd | Silver | Isla Murray | 3 |

**5. Business interpretation.** Seventeen customers had both a breached P1 and at least three repeat incidents in the last 90 days. Ten of them are Platinum, six are Gold and one is Silver. Granite Renewables plc (13 repeats), Abbey Software Ltd (11) and Ironbridge Bank plc (9) lead the list. A P1 breach on a customer who is already seeing the same problem repeatedly is a strong churn signal, and the list gives each CSM a named action.

---

## Q13

### Out-of-hours queueing effect

**1. Business question.** For P3/P4 tickets, how much more often do out-of-hours tickets breach, by team operating model?

**2. SQL solution** (`database/queries/03_ctes_subqueries.sql`)

```sql
WITH labelled AS (
    SELECT t.operating_model,
           CASE WHEN f.is_out_of_hours THEN 'out_of_hours' ELSE 'in_hours' END AS logged,
           f.sla_breached
    FROM analytics.fact_tickets f
    JOIN analytics.dim_team t USING (team_id)
    WHERE f.priority IN ('P3', 'P4')
)
SELECT operating_model,
       count(*) FILTER (WHERE logged = 'in_hours' AND sla_breached IS NOT NULL)     AS n_in_hours,
       round(100 * avg(sla_breached::int) FILTER (WHERE logged = 'in_hours'), 1)     AS breach_pct_in_hours,
       count(*) FILTER (WHERE logged = 'out_of_hours' AND sla_breached IS NOT NULL) AS n_out_of_hours,
       round(100 * avg(sla_breached::int) FILTER (WHERE logged = 'out_of_hours'), 1) AS breach_pct_out_of_hours,
       round(avg(sla_breached::int) FILTER (WHERE logged = 'out_of_hours')
             / NULLIF(avg(sla_breached::int) FILTER (WHERE logged = 'in_hours'), 0), 2) AS relative_risk
FROM labelled
GROUP BY operating_model
ORDER BY relative_risk DESC;
```

**3. Why this technique.** CTE + CASE to label groups, conditional aggregation, ratio of rates. Separates 24x7 teams from business-hours teams to isolate the queueing mechanism.

**4. Actual result** - 3 row(s), 56 ms including client round-trip; saved to `database/query_results/Q13.csv`

| operating_model | n_in_hours | breach_pct_in_hours | n_out_of_hours | breach_pct_out_of_hours | relative_risk |
|---|---|---|---|---|---|
| Business Hours | 5036 | 11.7 | 1606 | 31.1 | 2.66 |
| Business Hours + On-call | 2372 | 16.1 | 745 | 30.9 | 1.91 |
| 24x7 | 5822 | 12.5 | 1838 | 12.8 | 1.02 |

**5. Business interpretation.** For P3/P4 tickets handled by business-hours teams, tickets logged out of hours breach 2.7 times as often as tickets logged in hours (31.1% vs 11.7%). The ratio is 1.9 for on-call teams. 24x7 teams show no difference (1.02). The mechanism is queueing: the ticket waits overnight or over the weekend while the SLA clock runs. **Options:** pause the SLA clock outside the customer's contracted hours, or extend triage cover for business-hours teams. Either would remove most of this breach source without any change to how the work itself is done.

---

## Q14

### Top 3 customers by volume within each industry

**1. Business question.** Who are the three highest-volume customers in every industry?

**2. SQL solution** (`database/queries/04_window_functions.sql`)

```sql
WITH ranked AS (
    SELECT industry, customer_name, sla_level, tickets, sla_breach_pct,
           row_number() OVER (PARTITION BY industry ORDER BY tickets DESC, customer_name) AS rn
    FROM analytics.customer_summary
    WHERE industry <> 'Unknown'
)
SELECT industry, rn AS rank_in_industry, customer_name, sla_level, tickets, sla_breach_pct
FROM ranked
WHERE rn <= 3
ORDER BY industry, rn;
```

**3. Why this technique.** ROW_NUMBER() OVER (PARTITION BY industry ORDER BY tickets DESC). ROW_NUMBER gives exactly N rows per group even when volumes tie (top-N-per-group pattern).

**4. Actual result** - 30 row(s), 98 ms including client round-trip; saved to `database/query_results/Q14.csv`

| industry | rank_in_industry | customer_name | sla_level | tickets | sla_breach_pct |
|---|---|---|---|---|---|
| Education | 1 | Ullswater Learning | Platinum | 118 | 31.03 |
| Education | 2 | Foxley Learning | Platinum | 117 | 27.19 |
| Education | 3 | Ashford College | Gold | 106 | 18.87 |
| Energy & Utilities | 1 | Granite Renewables plc | Platinum | 220 | 37.33 |
| Energy & Utilities | 2 | Exmoor Water Ltd | Silver | 88 | 4.65 |
| Energy & Utilities | 3 | Juniper Renewables Group | Platinum | 78 | 29.33 |
| Financial Services | 1 | Kingsmere Partners Group | Gold | 226 | 18.92 |
| Financial Services | 2 | Ironbridge Bank plc | Gold | 221 | 19.62 |
| Financial Services | 3 | Hartwell Bank Group | Silver | 132 | 9.3 |
| Healthcare | 1 | Vale Health Ltd | Silver | 212 | 8.61 |
| Healthcare | 2 | Clifton Clinics Ltd | Platinum | 135 | 38.76 |
| Healthcare | 3 | Portland Care Group plc | Platinum | 127 | 30.16 |
| Logistics | 1 | Foxley Logistics Ltd | Platinum | 144 | 33.33 |
| Logistics | 2 | Moorland Transport Ltd | Platinum | 142 | 31.43 |
| Logistics | 3 | Clifton Logistics plc | Silver | 138 | 6.77 |
| Manufacturing | 1 | Osprey Engineering Group | Gold | 295 | 21.33 |
| Manufacturing | 2 | Northgate Engineering plc | Platinum | 218 | 31.43 |
| Manufacturing | 3 | Dalton Industries Group | Gold | 205 | 20.92 |
| Professional Services | 1 | Granite Accountants Group | Platinum | 236 | 32.31 |
| Professional Services | 2 | Bramley Legal Ltd | Platinum | 141 | 29.2 |
| Professional Services | 3 | Brightwater Advisory plc | Gold | 113 | 27.27 |
| Public Sector | 1 | Riverside Authority | Gold | 124 | 21.19 |
| Public Sector | 2 | Ironbridge Housing Trust | Gold | 120 | 17.8 |
| Public Sector | 3 | Kestrel Services | Gold | 114 | 20.54 |
| Retail | 1 | Albion Home Ltd | Gold | 175 | 23.26 |

_Showing 25 of 30 rows - full result in the CSV._

**5. Business interpretation.** Within each industry, the top three customers by volume are a mixed group. Many are Platinum customers breaching 27–39% of the time, such as Granite Renewables (220 tickets, 37.3%) and Clifton Clinics (135 tickets, 38.8%). Others are Silver customers breaching around 5–9%. This matches Q06: contract level, not industry, separates the experience of high-volume customers. Account plans for the largest Platinum accounts should be the first priority.

---

## Q15

### Team breach-rate ranking, 2024 vs 2025

**1. Business question.** How did each team's breach-rate rank change between 2024 and 2025?

**2. SQL solution** (`database/queries/04_window_functions.sql`)

```sql
WITH yearly AS (
    SELECT team_id, extract(year FROM created_at)::int AS yr,
           round(100 * avg(sla_breached::int), 1) AS breach_pct
    FROM analytics.fact_tickets
    GROUP BY team_id, extract(year FROM created_at)
), ranked AS (
    SELECT y.*,
           rank()       OVER (PARTITION BY yr ORDER BY breach_pct DESC) AS breach_rank,
           dense_rank() OVER (PARTITION BY yr ORDER BY round(breach_pct / 5) * 5 DESC) AS band_dense_rank
    FROM yearly y
)
SELECT t.team_name,
       a.breach_pct AS breach_pct_2024, a.breach_rank AS rank_2024,
       b.breach_pct AS breach_pct_2025, b.breach_rank AS rank_2025,
       b.band_dense_rank AS dense_rank_5pt_band_2025,
       round(b.breach_pct - a.breach_pct, 1) AS change_pp
FROM ranked a
JOIN ranked b ON b.team_id = a.team_id AND b.yr = 2025
JOIN analytics.dim_team t ON t.team_id = a.team_id
WHERE a.yr = 2024
ORDER BY rank_2025;
```

**3. Why this technique.** RANK() and DENSE_RANK() partitioned by year, then a self-join to compare years. RANK leaves gaps after ties, DENSE_RANK does not; both are shown to illustrate the difference.

**4. Actual result** - 8 row(s), 72 ms including client round-trip; saved to `database/query_results/Q15.csv`

| team_name | breach_pct_2024 | rank_2024 | breach_pct_2025 | rank_2025 | dense_rank_5pt_band_2025 | change_pp |
|---|---|---|---|---|---|---|
| Network Operations | 29.1 | 1 | 40.1 | 1 | 1 | 11.0 |
| Infrastructure & Cloud | 22.6 | 3 | 32.3 | 2 | 2 | 9.7 |
| Application Support | 24.7 | 2 | 26.7 | 3 | 3 | 2.0 |
| End User Computing | 13.7 | 4 | 18.2 | 4 | 4 | 4.5 |
| Database Services | 7.1 | 6 | 13.8 | 5 | 5 | 6.7 |
| Identity & Access Management | 10.2 | 5 | 12.6 | 6 | 5 | 2.4 |
| Security Operations | 4.9 | 7 | 6.9 | 7 | 6 | 2.0 |
| Service Desk | 3.0 | 8 | 5.0 | 8 | 6 | 2.0 |

**5. Business interpretation.** Every team's breach rate rose between 2024 and 2025. Network Operations (+11.0 points, to 40.1%) and Infrastructure & Cloud (+9.7, to 32.3%) deteriorated most. Infrastructure & Cloud overtook Application Support for second place. The ranking order barely changed, so the decline is organisation-wide, consistent with volume growth on flat headcount, rather than a single team failing. The dense-rank column groups teams into 5-point bands. It shows Identity & Access Management and Database Services in the same band, so their rank difference is not meaningful.

---

## Q16

### Month-over-month change in SLA breach rate

**1. Business question.** How did the breach rate move month to month, and which months saw the biggest jumps?

**2. SQL solution** (`database/queries/04_window_functions.sql`)

```sql
SELECT to_char(created_month, 'YYYY-MM')                    AS month,
       tickets,
       sla_breach_pct,
       lag(sla_breach_pct) OVER (ORDER BY created_month)    AS prev_month_pct,
       round(sla_breach_pct - lag(sla_breach_pct) OVER (ORDER BY created_month), 2) AS mom_change_pp,
       round(100.0 * (tickets - lag(tickets) OVER (ORDER BY created_month))
             / lag(tickets) OVER (ORDER BY created_month), 1) AS volume_mom_pct
FROM analytics.kpi_monthly
ORDER BY created_month;
```

**3. Why this technique.** LAG() over months for previous-period comparison. LAG reads the previous row in order, so MoM change needs no self-join.

**4. Actual result** - 24 row(s), 50 ms including client round-trip; saved to `database/query_results/Q16.csv`

| month | tickets | sla_breach_pct | prev_month_pct | mom_change_pp | volume_mom_pct |
|---|---|---|---|---|---|
| 2024-01 | 869 | 15.5 |  |  |  |
| 2024-02 | 734 | 12.48 | 15.50 | -3.02 | -15.5 |
| 2024-03 | 782 | 15.71 | 12.48 | 3.23 | 6.5 |
| 2024-04 | 790 | 12.47 | 15.71 | -3.24 | 1.0 |
| 2024-05 | 863 | 16.17 | 12.47 | 3.70 | 9.2 |
| 2024-06 | 809 | 14.64 | 16.17 | -1.53 | -6.3 |
| 2024-07 | 876 | 13.84 | 14.64 | -0.80 | 8.3 |
| 2024-08 | 716 | 12.57 | 13.84 | -1.27 | -18.3 |
| 2024-09 | 858 | 15.38 | 12.57 | 2.81 | 19.8 |
| 2024-10 | 1007 | 20.95 | 15.38 | 5.57 | 17.4 |
| 2024-11 | 927 | 17.61 | 20.95 | -3.34 | -7.9 |
| 2024-12 | 787 | 14.23 | 17.61 | -3.38 | -15.1 |
| 2025-01 | 1046 | 21.1 | 14.23 | 6.87 | 32.9 |
| 2025-02 | 866 | 15.78 | 21.10 | -5.32 | -17.2 |
| 2025-03 | 1104 | 23.24 | 15.78 | 7.46 | 27.5 |
| 2025-04 | 864 | 16.31 | 23.24 | -6.93 | -21.7 |
| 2025-05 | 963 | 20.3 | 16.31 | 3.99 | 11.5 |
| 2025-06 | 1002 | 19.09 | 20.30 | -1.21 | 4.0 |
| 2025-07 | 1021 | 20.73 | 19.09 | 1.64 | 1.9 |
| 2025-08 | 861 | 16.57 | 20.73 | -4.16 | -15.7 |
| 2025-09 | 1157 | 27.3 | 16.57 | 10.73 | 34.4 |
| 2025-10 | 1163 | 22.14 | 27.30 | -5.16 | 0.5 |
| 2025-11 | 1064 | 20.67 | 22.14 | -1.47 | -8.5 |
| 2025-12 | 961 | 19.6 | 20.67 | -1.07 | -9.7 |

**5. Business interpretation.** Month-to-month changes are noisy, ranging from −6.9 to +10.7 points, so a single month should never trigger action. The largest jumps line up with the major-incident spikes found in Q23: September 2025 (+10.7 points, the cloud incident), March 2025 (+7.5, the VPN carrier outage) and October 2024 (+5.6, the integration failure). Breach rates also rise in months where volume jumps, such as January 2025, when volume was up 32.9% and breaches rose 6.9 points.

---

## Q17

### How soon does the same problem come back?

**1. Business question.** After an incident, how many days until the same customer raises the same subcategory again?

**2. SQL solution** (`database/queries/04_window_functions.sql`)

```sql
WITH gaps AS (
    SELECT category,
           extract(epoch FROM lead(created_at) OVER (PARTITION BY customer_id, subcategory_id
                                                   ORDER BY created_at) - created_at) / 86400.0 AS days_to_next
    FROM analytics.fact_tickets
    WHERE is_incident AND NOT customer_is_placeholder AND subcategory_id IS NOT NULL
)
SELECT category,
       count(days_to_next)                                                   AS recurrences,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY days_to_next))::numeric, 1) AS median_days_to_next,
       round(100.0 * count(*) FILTER (WHERE days_to_next <= 7) / NULLIF(count(days_to_next), 0), 1)
                                                                             AS pct_within_7_days,
       round(100.0 * count(*) FILTER (WHERE days_to_next <= 30) / NULLIF(count(days_to_next), 0), 1)
                                                                             AS pct_within_30_days
FROM gaps
GROUP BY category
ORDER BY pct_within_30_days DESC;
```

**3. Why this technique.** LEAD() over customer + subcategory, then percentile_cont on the gap, by category. LEAD looks forward to the next event in the partition - the natural way to measure recurrence time.

**4. Actual result** - 10 row(s), 74 ms including client round-trip; saved to `database/query_results/Q17.csv`

| category | recurrences | median_days_to_next | pct_within_7_days | pct_within_30_days |
|---|---|---|---|---|
| Business Applications | 964 | 67.1 | 14.3 | 36.2 |
| Network | 1635 | 72.0 | 10.0 | 28.0 |
| Email & Collaboration | 1815 | 83.1 | 6.1 | 24.4 |
| Infrastructure | 908 | 98.6 | 7.6 | 22.5 |
| Hardware | 1120 | 101.7 | 5.0 | 20.0 |
| Cloud Services | 427 | 118.1 | 5.2 | 19.7 |
| Access & Identity | 1014 | 92.0 | 5.6 | 19.4 |
| Software | 630 | 106.5 | 4.8 | 18.6 |
| Security | 606 | 124.6 | 3.0 | 14.0 |
| Database | 210 | 127.1 | 1.0 | 12.9 |

**5. Business interpretation.** Business Applications and Network issues recur fastest. When a customer has one, 36% and 28% of the time respectively the same customer raises the same subcategory again within 30 days, and 14% and 10% within a week. Database and Security issues recur least (13–14% within 30 days). Fast recurrence suggests fixes that are not permanent, such as workarounds and known errors (see Q35). These two categories are the strongest candidates for problem-management investigations.

---

## Q18

### Running total of tickets and breaches by year

**1. Business question.** How do cumulative ticket and breach counts build through each year?

**2. SQL solution** (`database/queries/04_window_functions.sql`)

```sql
SELECT extract(year FROM created_month)::int                   AS year,
       to_char(created_month, 'Mon')                           AS month,
       tickets,
       sum(tickets) OVER w                                     AS ytd_tickets,
       breaches,
       sum(breaches) OVER w                                    AS ytd_breaches,
       round(100.0 * sum(breaches) OVER w / sum(resolved_in_scope) OVER w, 2) AS ytd_breach_pct
FROM (
    SELECT created_month, count(*) AS tickets,
           count(*) FILTER (WHERE sla_breached)      AS breaches,
           count(*) FILTER (WHERE in_sla_population) AS resolved_in_scope
    FROM analytics.fact_tickets
    GROUP BY created_month
) m
WINDOW w AS (PARTITION BY extract(year FROM created_month) ORDER BY created_month)
ORDER BY created_month;
```

**3. Why this technique.** SUM() OVER (PARTITION BY year ORDER BY month) running totals. A running total resets each year via PARTITION BY - year-to-date reporting.

**4. Actual result** - 24 row(s), 45 ms including client round-trip; saved to `database/query_results/Q18.csv`

| year | month | tickets | ytd_tickets | breaches | ytd_breaches | ytd_breach_pct |
|---|---|---|---|---|---|---|
| 2024 | Jan | 869 | 869 | 133 | 133 | 15.5 |
| 2024 | Feb | 734 | 1603 | 90 | 223 | 14.12 |
| 2024 | Mar | 782 | 2385 | 121 | 344 | 14.64 |
| 2024 | Apr | 790 | 3175 | 97 | 441 | 14.1 |
| 2024 | May | 863 | 4038 | 137 | 578 | 14.54 |
| 2024 | Jun | 809 | 4847 | 117 | 695 | 14.56 |
| 2024 | Jul | 876 | 5723 | 120 | 815 | 14.45 |
| 2024 | Aug | 716 | 6439 | 89 | 904 | 14.24 |
| 2024 | Sep | 858 | 7297 | 130 | 1034 | 14.38 |
| 2024 | Oct | 1007 | 8304 | 207 | 1241 | 15.17 |
| 2024 | Nov | 927 | 9231 | 161 | 1402 | 15.42 |
| 2024 | Dec | 787 | 10018 | 110 | 1512 | 15.32 |
| 2025 | Jan | 1046 | 1046 | 219 | 219 | 21.1 |
| 2025 | Feb | 866 | 1912 | 134 | 353 | 18.71 |
| 2025 | Mar | 1104 | 3016 | 254 | 607 | 20.37 |
| 2025 | Apr | 864 | 3880 | 139 | 746 | 19.47 |
| 2025 | May | 963 | 4843 | 192 | 938 | 19.63 |
| 2025 | Jun | 1002 | 5845 | 188 | 1126 | 19.54 |
| 2025 | Jul | 1021 | 6866 | 209 | 1335 | 19.72 |
| 2025 | Aug | 861 | 7727 | 139 | 1474 | 19.37 |
| 2025 | Sep | 1157 | 8884 | 311 | 1785 | 20.4 |
| 2025 | Oct | 1163 | 10047 | 254 | 2039 | 20.6 |
| 2025 | Nov | 1064 | 11111 | 205 | 2244 | 20.61 |
| 2025 | Dec | 961 | 12072 | 148 | 2392 | 20.54 |

**5. Business interpretation.** 2024 ended with 10,018 tickets and a year-to-date breach rate of 15.3%. 2025 ended with 12,072 tickets (+20.5%) and 20.5%. The 2025 year-to-date line never drops below 18.7%, so the deterioration was present from January rather than building up during the year. This is the headline trend for the Head of IT Operations.

---

## Q19

### Three-month moving averages

**1. Business question.** What is the underlying trend in breach rate and median resolution once month-to-month noise is smoothed?

**2. SQL solution** (`database/queries/04_window_functions.sql`)

```sql
SELECT to_char(created_month, 'YYYY-MM')                                     AS month,
       sla_breach_pct,
       round(avg(sla_breach_pct) OVER w, 2)                                  AS breach_pct_3m_avg,
       median_resolution_hours,
       round(avg(median_resolution_hours) OVER w, 2)                         AS median_res_3m_avg,
       avg_csat,
       round(avg(avg_csat) OVER w, 3)                                        AS csat_3m_avg,
       CASE WHEN count(*) OVER w < 3 THEN 'partial window' END               AS note
FROM analytics.kpi_monthly
WINDOW w AS (ORDER BY created_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
ORDER BY created_month;
```

**3. Why this technique.** AVG() OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW). A ROWS frame gives a trailing 3-month moving average; the first two months are marked partial.

**4. Actual result** - 24 row(s), 64 ms including client round-trip; saved to `database/query_results/Q19.csv`

| month | sla_breach_pct | breach_pct_3m_avg | median_resolution_hours | median_res_3m_avg | avg_csat | csat_3m_avg | note |
|---|---|---|---|---|---|---|---|
| 2024-01 | 15.5 | 15.5 | 13.21 | 13.21 | 4.017 | 4.017 | partial window |
| 2024-02 | 12.48 | 13.99 | 11.61 | 12.41 | 4.062 | 4.04 | partial window |
| 2024-03 | 15.71 | 14.56 | 12.99 | 12.6 | 4.069 | 4.049 |  |
| 2024-04 | 12.47 | 13.55 | 11.52 | 12.04 | 4.051 | 4.061 |  |
| 2024-05 | 16.17 | 14.78 | 13.66 | 12.72 | 3.987 | 4.036 |  |
| 2024-06 | 14.64 | 14.43 | 12.06 | 12.41 | 4.014 | 4.017 |  |
| 2024-07 | 13.84 | 14.88 | 13.77 | 13.16 | 4.022 | 4.008 |  |
| 2024-08 | 12.57 | 13.68 | 12.48 | 12.77 | 4.071 | 4.036 |  |
| 2024-09 | 15.38 | 13.93 | 14.43 | 13.56 | 4.07 | 4.054 |  |
| 2024-10 | 20.95 | 16.3 | 16.92 | 14.61 | 3.86 | 4.0 |  |
| 2024-11 | 17.61 | 17.98 | 14.57 | 15.31 | 4.043 | 3.991 |  |
| 2024-12 | 14.23 | 17.6 | 12.76 | 14.75 | 4.003 | 3.969 |  |
| 2025-01 | 21.1 | 17.65 | 17.85 | 15.06 | 3.894 | 3.98 |  |
| 2025-02 | 15.78 | 17.04 | 14.23 | 14.95 | 3.946 | 3.948 |  |
| 2025-03 | 23.24 | 20.04 | 16.06 | 16.05 | 3.95 | 3.93 |  |
| 2025-04 | 16.31 | 18.44 | 15.14 | 15.14 | 3.98 | 3.959 |  |
| 2025-05 | 20.3 | 19.95 | 15.04 | 15.41 | 3.907 | 3.946 |  |
| 2025-06 | 19.09 | 18.57 | 15.62 | 15.27 | 3.986 | 3.958 |  |
| 2025-07 | 20.73 | 20.04 | 17.25 | 15.97 | 3.913 | 3.935 |  |
| 2025-08 | 16.57 | 18.8 | 13.08 | 15.32 | 4.06 | 3.986 |  |
| 2025-09 | 27.3 | 21.53 | 18.43 | 16.25 | 3.763 | 3.912 |  |
| 2025-10 | 22.14 | 22.0 | 18.75 | 16.75 | 3.947 | 3.923 |  |
| 2025-11 | 20.67 | 23.37 | 18.24 | 18.47 | 3.932 | 3.881 |  |
| 2025-12 | 19.6 | 20.8 | 15.48 | 17.49 | 3.822 | 3.9 |  |

**5. Business interpretation.** Smoothing over three months shows a clear upward trend in breach rate: about 14% through mid-2024, rising to 19–23% through the second half of 2025. Median resolution time rose from about 12–13 hours to 16–18 hours over the same period, and average CSAT drifted down from about 4.05 to 3.90. All three move together, which is consistent with a capacity problem. The first two months have a partial window and are labelled as such.

---

## Q20

### Customer volume quartiles

**1. Business question.** How do outcomes differ between low- and high-volume customers?

**2. SQL solution** (`database/queries/04_window_functions.sql`)

```sql
WITH q AS (
    SELECT cs.*, ntile(4) OVER (ORDER BY tickets) AS volume_quartile
    FROM analytics.customer_summary cs
)
SELECT volume_quartile,
       count(*)                                    AS customers,
       min(tickets)                                AS min_tickets,
       max(tickets)                                AS max_tickets,
       sum(tickets)                                AS total_tickets,
       round(100.0 * sum(tickets) / sum(sum(tickets)) OVER (), 1) AS pct_of_all_tickets,
       round(100.0 * sum(repeat_incidents) / NULLIF(sum(incidents), 0), 1) AS repeat_incident_pct,
       round(avg(sla_breach_pct), 1)               AS avg_customer_breach_pct
FROM q
GROUP BY volume_quartile
ORDER BY volume_quartile;
```

**3. Why this technique.** NTILE(4) to bucket customers into volume quartiles, then aggregate per bucket. NTILE creates equal-sized segments without hard-coding thresholds.

**4. Actual result** - 4 row(s), 73 ms including client round-trip; saved to `database/query_results/Q20.csv`

| volume_quartile | customers | min_tickets | max_tickets | total_tickets | pct_of_all_tickets | repeat_incident_pct | avg_customer_breach_pct |
|---|---|---|---|---|---|---|---|
| 1 | 125 | 1 | 16 | 1302 | 5.9 | 1.8 | 10.5 |
| 2 | 125 | 16 | 28 | 2740 | 12.4 | 3.7 | 12.3 |
| 3 | 125 | 28 | 55 | 5141 | 23.3 | 7.1 | 15.9 |
| 4 | 124 | 55 | 295 | 12897 | 58.4 | 17.8 | 19.6 |

**5. Business interpretation.** The top quartile of customers by volume (124 customers) generates 58.4% of all tickets and has a repeat-incident rate of 17.8%, about ten times the bottom quartile's 1.8%. Their average breach rate is also the highest (19.6%). Customer success effort should concentrate on this quartile. Problem management for these customers would remove a disproportionate share of total volume.

---

## Q21

### When do tickets arrive? (weekday x time band)

**1. Business question.** How is ticket volume distributed across the week and the working day?

**2. SQL solution** (`database/queries/05_time_series.sql`)

```sql
SELECT to_char(created_at, 'ID-Dy')                                          AS weekday,
       count(*) FILTER (WHERE extract(hour FROM created_at) < 8)              AS "00-08",
       count(*) FILTER (WHERE extract(hour FROM created_at) BETWEEN 8 AND 11) AS "08-12",
       count(*) FILTER (WHERE extract(hour FROM created_at) BETWEEN 12 AND 13) AS "12-14",
       count(*) FILTER (WHERE extract(hour FROM created_at) BETWEEN 14 AND 17) AS "14-18",
       count(*) FILTER (WHERE extract(hour FROM created_at) >= 18)            AS "18-24",
       count(*)                                                              AS total,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                    AS pct_of_week
FROM analytics.fact_tickets
GROUP BY to_char(created_at, 'ID-Dy')
ORDER BY weekday;
```

**3. Why this technique.** EXTRACT(isodow / hour), CASE time bands, conditional aggregation into a heatmap grid. Shows staffing demand; EXTRACT and CASE turn timestamps into business time bands.

**4. Actual result** - 7 row(s), 67 ms including client round-trip; saved to `database/query_results/Q21.csv`

| weekday | 00-08 | 08-12 | 12-14 | 14-18 | 18-24 | total | pct_of_week |
|---|---|---|---|---|---|---|---|
| 1-Mon | 275 | 1573 | 700 | 1390 | 418 | 4356 | 19.7 |
| 2-Tue | 310 | 1769 | 703 | 1467 | 389 | 4638 | 21.0 |
| 3-Wed | 283 | 1418 | 610 | 1263 | 382 | 3956 | 17.9 |
| 4-Thu | 251 | 1447 | 602 | 1237 | 369 | 3906 | 17.7 |
| 5-Fri | 244 | 1192 | 493 | 1072 | 338 | 3339 | 15.1 |
| 6-Sat | 288 | 222 | 116 | 219 | 222 | 1067 | 4.8 |
| 7-Sun | 198 | 177 | 99 | 169 | 185 | 828 | 3.7 |

**5. Business interpretation.** Monday and Tuesday are the busiest days (19.7% and 21.0% of weekly volume), and volume falls through the week to Friday (15.1%). Weekends carry only 8.5% of volume combined. The 08:00–12:00 band is the daily peak on every weekday. About 1,900 weekday tickets arrived after 18:00 over the two years, and these feed the out-of-hours queue described in Q13. Staffing should be weighted towards Monday and Tuesday mornings.

---

## Q22

### Year-over-year by quarter

**1. Business question.** How did volume, breach rate and CSAT change between each quarter of 2024 and the same quarter of 2025?

**2. SQL solution** (`database/queries/05_time_series.sql`)

```sql
SELECT 'Q' || extract(quarter FROM created_at)                                 AS quarter,
       count(*) FILTER (WHERE extract(year FROM created_at) = 2024)            AS tickets_2024,
       count(*) FILTER (WHERE extract(year FROM created_at) = 2025)            AS tickets_2025,
       round(100.0 * (count(*) FILTER (WHERE extract(year FROM created_at) = 2025)
                    - count(*) FILTER (WHERE extract(year FROM created_at) = 2024))
             / count(*) FILTER (WHERE extract(year FROM created_at) = 2024), 1) AS volume_yoy_pct,
       round(100 * avg(sla_breached::int) FILTER (WHERE extract(year FROM created_at) = 2024), 1) AS breach_pct_2024,
       round(100 * avg(sla_breached::int) FILTER (WHERE extract(year FROM created_at) = 2025), 1) AS breach_pct_2025,
       round(avg(customer_satisfaction) FILTER (WHERE extract(year FROM created_at) = 2024), 2) AS csat_2024,
       round(avg(customer_satisfaction) FILTER (WHERE extract(year FROM created_at) = 2025), 2) AS csat_2025
FROM analytics.fact_tickets
GROUP BY extract(quarter FROM created_at)
ORDER BY quarter;
```

**3. Why this technique.** date_part, conditional aggregation by year, YoY growth calculation. Comparing like-for-like quarters removes seasonality from the trend.

**4. Actual result** - 4 row(s), 82 ms including client round-trip; saved to `database/query_results/Q22.csv`

| quarter | tickets_2024 | tickets_2025 | volume_yoy_pct | breach_pct_2024 | breach_pct_2025 | csat_2024 | csat_2025 |
|---|---|---|---|---|---|---|---|
| Q1 | 2385 | 3016 | 26.5 | 14.6 | 20.4 | 4.05 | 3.93 |
| Q2 | 2462 | 2829 | 14.9 | 14.5 | 18.6 | 4.02 | 3.96 |
| Q3 | 2450 | 3039 | 24.0 | 14.0 | 22.1 | 4.05 | 3.9 |
| Q4 | 2721 | 3188 | 17.2 | 17.9 | 21.0 | 3.96 | 3.91 |

**5. Business interpretation.** Every quarter of 2025 had more tickets than the same quarter of 2024, by 15–27%, and a higher breach rate, by 3.1–8.1 points. CSAT was lower in every quarter as well. Because quarters are compared like for like, seasonality is ruled out: the deterioration is a genuine year-on-year trend.

---

## Q23

### Detecting volume spikes (major incidents)

**1. Business question.** Which days had volume far above their recent normal level?

**2. SQL solution** (`database/queries/05_time_series.sql`)

```sql
WITH daily AS (
    SELECT d.date, d.day_name, d.is_working_day, count(f.ticket_id) AS tickets
    FROM analytics.dim_date d
    LEFT JOIN analytics.fact_tickets f ON f.created_date = d.date
    GROUP BY d.date, d.day_name, d.is_working_day
), baseline AS (
    SELECT daily.*,
           avg(tickets) FILTER (WHERE is_working_day) OVER (
               ORDER BY date RANGE BETWEEN interval '28 days' PRECEDING AND interval '1 day' PRECEDING
           ) AS prior_28d_working_day_avg
    FROM daily
)
SELECT date, day_name, tickets,
       round(prior_28d_working_day_avg, 1)                           AS prior_28d_avg,
       round(tickets / NULLIF(prior_28d_working_day_avg, 0), 2)      AS ratio_to_normal,
       (SELECT string_agg(sub || ' (' || n || ')', ', ' ORDER BY n DESC)
        FROM (SELECT f.subcategory AS sub, count(*) AS n FROM analytics.fact_tickets f
              WHERE f.created_date = b.date GROUP BY f.subcategory ORDER BY n DESC LIMIT 2) top) AS top_subcategories
FROM baseline b
WHERE prior_28d_working_day_avg IS NOT NULL
ORDER BY ratio_to_normal DESC
LIMIT 8;
```

**3. Why this technique.** Calendar LEFT JOIN (zero-filled days), RANGE window over a 28-day interval, ratio to baseline. The date dimension guarantees days with no tickets still count; RANGE uses real dates, not rows.

**4. Actual result** - 8 row(s), 88 ms including client round-trip; saved to `database/query_results/Q23.csv`

| date | day_name | tickets | prior_28d_avg | ratio_to_normal | top_subcategories |
|---|---|---|---|---|---|
| 2025-09-23 | Tuesday | 129 | 42.9 | 3.01 | Azure Resource Issue (72), ERP Issue (5) |
| 2025-03-11 | Tuesday | 124 | 41.4 | 3.0 | VPN Connectivity (85), Mailbox Issue (5) |
| 2024-10-08 | Tuesday | 89 | 36.4 | 2.45 | Integration / API Failure (42), AWS Resource Issue (3) |
| 2025-06-03 | Tuesday | 69 | 41.1 | 1.68 | Account Lockout (8), Data Correction Request (5) |
| 2024-05-13 | Monday | 57 | 34.9 | 1.63 | Laptop / Desktop Fault (4), Phishing Report (4) |
| 2024-09-03 | Tuesday | 48 | 30.3 | 1.58 | Mailbox Issue (4), VPN Connectivity (4) |
| 2025-01-06 | Monday | 54 | 34.3 | 1.57 | Mailbox Issue (4), Microsoft Teams (4) |
| 2024-07-30 | Tuesday | 54 | 34.9 | 1.55 | Software Installation (5), MFA Issue (4) |

**5. Business interpretation.** The three days with the highest volume relative to normal are the three major incidents, with no false alarms: 23 September 2025 (Azure resource issue, 3.0 times normal), 11 March 2025 (VPN connectivity, 3.0 times) and 8 October 2024 (integration/API failure, 2.5 times). The next highest day reaches only 1.7 times normal, so a "more than twice normal" threshold separates major incidents cleanly. This could feed an automated major-incident alert.

---

## Q24

### Change-related incidents over time

**1. Business question.** Is the share of incidents caused by changes growing, and how do they perform against SLA?

**2. SQL solution** (`database/queries/05_time_series.sql`)

```sql
WITH q AS (
    SELECT date_trunc('quarter', created_at)::date AS quarter,
           count(*) FILTER (WHERE root_cause IS NOT NULL)                AS incidents_known_cause,
           count(*) FILTER (WHERE root_cause = 'Change-Related')         AS change_related,
           round(100 * avg(sla_breached::int) FILTER (WHERE root_cause = 'Change-Related'), 1) AS change_breach_pct,
           round(100 * avg(sla_breached::int) FILTER (WHERE root_cause <> 'Change-Related'), 1) AS other_breach_pct
    FROM analytics.fact_tickets
    WHERE is_incident AND is_resolved
    GROUP BY date_trunc('quarter', created_at)
)
SELECT to_char(quarter, 'YYYY-"Q"Q')                                  AS quarter,
       incidents_known_cause, change_related,
       round(100.0 * change_related / incidents_known_cause, 1)       AS change_share_pct,
       round(100.0 * change_related / incidents_known_cause
             - lag(100.0 * change_related / incidents_known_cause) OVER (ORDER BY quarter), 1) AS qoq_change_pp,
       change_breach_pct, other_breach_pct
FROM q
ORDER BY quarter;
```

**3. Why this technique.** date_trunc('quarter'), conditional aggregation, window LAG for quarter-over-quarter change. Tests the hypothesis that weak change control is a growing source of incidents (KPI-15).

**4. Actual result** - 8 row(s), 67 ms including client round-trip; saved to `database/query_results/Q24.csv`

| quarter | incidents_known_cause | change_related | change_share_pct | qoq_change_pp | change_breach_pct | other_breach_pct |
|---|---|---|---|---|---|---|
| 2024-Q1 | 1766 | 240 | 13.6 |  | 19.6 | 17.0 |
| 2024-Q2 | 1805 | 232 | 12.9 | -0.7 | 18.5 | 16.9 |
| 2024-Q3 | 1805 | 273 | 15.1 | 2.3 | 20.1 | 16.2 |
| 2024-Q4 | 2019 | 365 | 18.1 | 3.0 | 29.6 | 19.2 |
| 2025-Q1 | 2241 | 379 | 16.9 | -1.2 | 32.1 | 22.1 |
| 2025-Q2 | 2111 | 390 | 18.5 | 1.6 | 23.7 | 20.8 |
| 2025-Q3 | 2234 | 478 | 21.4 | 2.9 | 30.8 | 24.7 |
| 2025-Q4 | 2145 | 502 | 23.4 | 2.0 | 30.3 | 22.3 |

**5. Business interpretation.** Change-related incidents rose from 13.6% of incidents with a known root cause (Q1 2024) to 23.4% (Q4 2025). They also breach SLA more often than other incidents in every quarter, for example 30.3% vs 22.3% in Q4 2025. Change-related incidents are therefore both growing in number and harder to resolve within target. **Recommendation:** strengthen change management, through change advisory board review of high-risk changes, post-implementation review and better rollback plans, with KPI-15 as the measure of success.

---

## Q25

### Resolution-time percentiles by priority

**1. Business question.** What does the full distribution of resolution time look like per priority, against target?

**2. SQL solution** (`database/queries/06_sla_percentiles.sql`)

```sql
SELECT priority, resolved_tickets, mean_h,
       round(pct[1]::numeric, 1) AS p50_h,
       round(pct[2]::numeric, 1) AS p75_h,
       round(pct[3]::numeric, 1) AS p90_h,
       round(pct[4]::numeric, 1) AS p95_h,
       min_target_h, max_target_h
FROM (
    SELECT priority,
           count(*)                                    AS resolved_tickets,
           round(avg(resolution_time_hours), 1)        AS mean_h,
           percentile_cont(ARRAY[0.5, 0.75, 0.9, 0.95])
               WITHIN GROUP (ORDER BY resolution_time_hours) AS pct,
           min(sla_target_hours)                       AS min_target_h,
           max(sla_target_hours)                       AS max_target_h
    FROM analytics.fact_tickets
    WHERE in_duration_population
    GROUP BY priority
) s
ORDER BY priority;
```

**3. Why this technique.** percentile_cont with an array of fractions (P50/P75/P90/P95) in one pass. Means hide skew; percentiles show how long the slowest 10% of customers wait.

**4. Actual result** - 4 row(s), 61 ms including client round-trip; saved to `database/query_results/Q25.csv`

| priority | resolved_tickets | mean_h | p50_h | p75_h | p90_h | p95_h | min_target_h | max_target_h |
|---|---|---|---|---|---|---|---|---|
| P1 | 893 | 5.8 | 4.7 | 7.5 | 10.9 | 14.3 | 4.0 | 12.0 |
| P2 | 3182 | 11.3 | 7.6 | 14.7 | 25.1 | 33.6 | 8.0 | 36.0 |
| P3 | 10331 | 25.2 | 16.6 | 34.0 | 60.0 | 79.3 | 24.0 | 96.0 |
| P4 | 7022 | 38.0 | 23.4 | 51.1 | 87.8 | 122.4 | 72.0 | 168.0 |

**5. Business interpretation.** Median resolution is broadly within target, but the tails are not. The P1 median is 4.7 hours, so more than half of all P1s take longer than the 4-hour Platinum/Gold target. The P2 90th percentile (25.1 hours) is three times the strictest P2 target of 8 hours. Averages such as the 25.2-hour mean for P3 hide this. SLA reporting should therefore use percentiles alongside breach rates.

---

## Q26

### How badly are SLAs missed?

**1. Business question.** When a ticket breaches, by how much does it overrun its target?

**2. SQL solution** (`database/queries/06_sla_percentiles.sql`)

```sql
WITH breached AS (
    SELECT priority, resolution_time_hours / sla_target_hours AS ratio
    FROM analytics.fact_tickets
    WHERE sla_breached
)
SELECT CASE width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0])
            WHEN 1 THEN '1.00-1.25x target'
            WHEN 2 THEN '1.25-1.5x'
            WHEN 3 THEN '1.5-2x'
            WHEN 4 THEN '2-3x'
            WHEN 5 THEN '3-5x'
            ELSE '5x or more' END                                   AS overrun_band,
       count(*)                                                     AS breaches,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)           AS pct_of_breaches,
       round(100.0 * sum(count(*)) OVER (ORDER BY width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0]))
             / sum(count(*)) OVER (), 1)                            AS cumulative_pct,
       count(*) FILTER (WHERE priority IN ('P1', 'P2'))             AS of_which_p1_p2
FROM breached
GROUP BY width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0])
ORDER BY width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0]);
```

**3. Why this technique.** width_bucket() on the overrun ratio, CASE labels, distribution percentages. Distinguishes near-misses (fixable with small process changes) from severe overruns.

**4. Actual result** - 6 row(s), 63 ms including client round-trip; saved to `database/query_results/Q26.csv`

| overrun_band | breaches | pct_of_breaches | cumulative_pct | of_which_p1_p2 |
|---|---|---|---|---|
| 1.00-1.25x target | 1130 | 28.9 | 28.9 | 302 |
| 1.25-1.5x | 647 | 16.6 | 45.5 | 188 |
| 1.5-2x | 923 | 23.6 | 69.2 | 298 |
| 2-3x | 679 | 17.4 | 86.6 | 242 |
| 3-5x | 336 | 8.6 | 95.2 | 140 |
| 5x or more | 189 | 4.8 | 100.0 | 67 |

**5. Business interpretation.** Close to half of all breaches (45.5%) miss the target by less than 50%, and 28.9% by less than 25%. These near-misses could be recovered by faster triage, or by alerting before a ticket breaches, rather than by deeper technical change. At the other end, 13.4% of breaches overrun by three times the target or more. These are the long-tail cases (vendor dependencies, tickets left open) that need individual review.

---

## Q27

### First-response SLA by priority and channel

**1. Business question.** Are first-response targets being met, and which channel/priority combinations miss most?

**2. SQL solution** (`database/queries/06_sla_percentiles.sql`)

```sql
SELECT priority,
       CASE WHEN grouping(channel) = 1 THEN '(all channels)' ELSE channel END AS channel,
       count(*) FILTER (WHERE in_response_population)               AS tickets,
       round(100 * avg(response_sla_met::int), 1)                   AS response_met_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY first_response_time_hours)
              FILTER (WHERE in_response_population))::numeric * 60, 0) AS median_response_minutes
FROM analytics.fact_tickets
WHERE channel IS NOT NULL
GROUP BY GROUPING SETS ((priority, channel), (priority))
ORDER BY priority, grouping(channel) DESC, response_met_pct;
```

**3. Why this technique.** GROUP BY GROUPING SETS for channel detail plus per-priority subtotals in one result. GROUPING SETS returns detail and subtotal rows together; GROUPING() labels the subtotal rows.

**4. Actual result** - 24 row(s), 69 ms including client round-trip; saved to `database/query_results/Q27.csv`

| priority | channel | tickets | response_met_pct | median_response_minutes |
|---|---|---|---|---|
| P1 | (all channels) | 920 | 96.1 | 4 |
| P1 | Email | 85 | 83.5 | 11 |
| P1 | Portal | 148 | 91.9 | 11 |
| P1 | Monitoring Alert | 226 | 95.6 | 7 |
| P1 | Chat | 56 | 100.0 | 3 |
| P1 | Phone | 405 | 100.0 | 2 |
| P2 | (all channels) | 3257 | 87.2 | 20 |
| P2 | Email | 682 | 74.5 | 36 |
| P2 | Portal | 1006 | 80.8 | 29 |
| P2 | Monitoring Alert | 668 | 94.6 | 16 |
| P2 | Chat | 352 | 97.4 | 11 |
| P2 | Phone | 549 | 99.1 | 7 |
| P3 | (all channels) | 10535 | 75.3 | 109 |
| P3 | Email | 2373 | 62.9 | 183 |
| P3 | Portal | 3477 | 70.5 | 152 |
| P3 | Monitoring Alert | 1347 | 79.1 | 90 |
| P3 | Chat | 1397 | 86.5 | 53 |
| P3 | Phone | 1941 | 88.3 | 38 |
| P4 | (all channels) | 7179 | 82.9 | 280 |
| P4 | Email | 1600 | 72.8 | 503 |
| P4 | Portal | 2698 | 79.5 | 386 |
| P4 | Monitoring Alert | 437 | 86.5 | 226 |
| P4 | Phone | 1458 | 92.6 | 100 |
| P4 | Chat | 986 | 92.7 | 134 |

**5. Business interpretation.** P1 first response is strong (96.1% within target, median 4 minutes). Performance degrades with priority: P2 87.2%, P3 75.3%. For every priority, email and the portal are the weakest channels. P3 email meets its response target only 62.9% of the time, against 88.3% for phone. Faster acknowledgement of email and portal tickets, for example an automated triage queue, is a low-cost improvement.

---

## Q28

### Escalation impact by priority

**1. Business question.** How much longer do escalated tickets take, and how much more often do they breach?

**2. SQL solution** (`database/queries/06_sla_percentiles.sql`)

```sql
SELECT priority,
       round(100 * avg(escalation_flag::int), 1)                                           AS escalation_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
              FILTER (WHERE in_duration_population AND NOT escalation_flag))::numeric, 1)  AS median_h_not_escalated,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
              FILTER (WHERE in_duration_population AND escalation_flag))::numeric, 1)      AS median_h_escalated,
       round(100 * avg(sla_breached::int) FILTER (WHERE NOT escalation_flag), 1)           AS breach_pct_not_escalated,
       round(100 * avg(sla_breached::int) FILTER (WHERE escalation_flag), 1)               AS breach_pct_escalated
FROM analytics.fact_tickets
GROUP BY priority
ORDER BY priority;
```

**3. Why this technique.** Conditional aggregation of medians with FILTER, ratio of escalated vs not. Compares like-for-like priorities so the priority mix does not distort the escalation effect.

**4. Actual result** - 4 row(s), 53 ms including client round-trip; saved to `database/query_results/Q28.csv`

| priority | escalation_pct | median_h_not_escalated | median_h_escalated | breach_pct_not_escalated | breach_pct_escalated |
|---|---|---|---|---|---|
| P1 | 56.3 | 1.5 | 6.7 | 15.0 | 65.3 |
| P2 | 38.8 | 4.3 | 13.7 | 13.9 | 46.4 |
| P3 | 20.2 | 13.3 | 32.7 | 15.3 | 37.8 |
| P4 | 11.6 | 19.7 | 58.1 | 6.5 | 25.9 |

**5. Business interpretation.** Escalated tickets take 2.5–4.5 times longer than non-escalated tickets of the same priority. For example, P2 tickets have a median of 13.7 hours when escalated, against 4.3 hours otherwise. Escalated P1s breach 65% of the time, against 15% for non-escalated P1s, and 56% of P1s are escalated. Escalation partly reflects genuinely harder work, so not every escalation can be avoided. The hand-off delay is still worth measuring, and better L1 knowledge-base content could resolve some of these tickets before they need escalating.

---

## Q29

### Root-cause Pareto with ABC classes

**1. Business question.** Which few root causes account for most incidents (80/20), and how do they perform?

**2. SQL solution** (`database/queries/07_pareto_root_cause.sql`)

```sql
WITH rc AS (
    SELECT root_cause, count(*) AS incidents,
           round(100 * avg(sla_breached::int), 1) AS breach_pct
    FROM analytics.fact_tickets
    WHERE is_incident AND is_resolved AND root_cause IS NOT NULL
    GROUP BY root_cause
), cum AS (
    SELECT rc.*,
           round(100.0 * incidents / sum(incidents) OVER (), 1) AS pct,
           round(100.0 * sum(incidents) OVER (ORDER BY incidents DESC, root_cause
                                              ROWS UNBOUNDED PRECEDING)
                 / sum(incidents) OVER (), 1)                   AS cumulative_pct
    FROM rc
)
SELECT root_cause, incidents, pct, cumulative_pct, breach_pct,
       CASE WHEN cumulative_pct - pct < 50 THEN 'A (first 50%)'
            WHEN cumulative_pct - pct < 80 THEN 'B (to 80%)'
            ELSE 'C (tail)' END                                 AS pareto_class
FROM cum
ORDER BY incidents DESC, root_cause;
```

**3. Why this technique.** Cumulative SUM() OVER (ORDER BY count DESC) / total, CASE into A/B/C classes. The cumulative share is the Pareto curve; ABC classes turn it into a priority list.

**4. Actual result** - 11 row(s), 49 ms including client round-trip; saved to `database/query_results/Q29.csv`

| root_cause | incidents | pct | cumulative_pct | breach_pct | pareto_class |
|---|---|---|---|---|---|
| Configuration Error | 3135 | 19.4 | 19.4 | 18.0 | A (first 50%) |
| Change-Related | 2859 | 17.7 | 37.2 | 26.8 | A (first 50%) |
| User Error | 2131 | 13.2 | 50.4 | 6.6 | A (first 50%) |
| Hardware Failure | 1476 | 9.2 | 59.5 | 26.5 | B (to 80%) |
| Third-Party / Vendor | 1296 | 8.0 | 67.6 | 37.8 | B (to 80%) |
| Software Defect | 1152 | 7.1 | 74.7 | 23.8 | B (to 80%) |
| Undetermined | 1090 | 6.8 | 81.5 | 20.7 | B (to 80%) |
| Known Error | 913 | 5.7 | 87.1 | 19.2 | C (tail) |
| Security Threat | 855 | 5.3 | 92.4 | 5.5 | C (tail) |
| Capacity / Performance | 779 | 4.8 | 97.3 | 25.2 | C (tail) |
| Network Connectivity | 440 | 2.7 | 100.0 | 34.8 | C (tail) |

**5. Business interpretation.** Three root causes, Configuration Error (19.4%), Change-Related (17.7%) and User Error (13.2%), account for half of all incidents. Seven causes reach 81.5%, so the distribution is flatter than a classic 80/20 pattern. The class-A causes differ greatly in how they perform against SLA. User Error breaches only 6.6% of the time and is cheap to fix through user education and self-service. Change-Related breaches 26.8% and is costly. Third-Party/Vendor issues are the worst-performing high-volume cause (37.8%), which points to supplier SLA management.

---

## Q30

### Which subcategories generate the SLA breaches?

**1. Business question.** Which subcategories account for 80% of all SLA breaches?

**2. SQL solution** (`database/queries/07_pareto_root_cause.sql`)

```sql
WITH s AS (
    SELECT category, subcategory, count(*) FILTER (WHERE sla_breached) AS breaches,
           round(100 * avg(sla_breached::int), 1) AS breach_rate_pct
    FROM analytics.fact_tickets
    WHERE subcategory IS NOT NULL
    GROUP BY category, subcategory
), c AS (
    SELECT s.*,
           round(100.0 * breaches / sum(breaches) OVER (), 1) AS pct_of_breaches,
           round(100.0 * sum(breaches) OVER (ORDER BY breaches DESC, subcategory ROWS UNBOUNDED PRECEDING)
                 / sum(breaches) OVER (), 1)                  AS cumulative_pct
    FROM s
)
SELECT category, subcategory, breaches, breach_rate_pct, pct_of_breaches, cumulative_pct
FROM c
WHERE cumulative_pct - pct_of_breaches < 80
ORDER BY breaches DESC;
```

**3. Why this technique.** Pareto on breach COUNT (not rate), cumulative window, filter on the running share. High-volume subcategories with moderate rates can matter more than rare ones with high rates.

**4. Actual result** - 19 row(s), 49 ms including client round-trip; saved to `database/query_results/Q30.csv`

| category | subcategory | breaches | breach_rate_pct | pct_of_breaches | cumulative_pct |
|---|---|---|---|---|---|
| Network | VPN Connectivity | 361 | 32.0 | 9.4 | 9.4 |
| Network | LAN / Switching | 262 | 52.0 | 6.8 | 16.1 |
| Cloud Services | Azure Resource Issue | 258 | 43.7 | 6.7 | 22.8 |
| Business Applications | ERP Issue | 254 | 34.6 | 6.6 | 29.4 |
| Hardware | Laptop / Desktop Fault | 245 | 26.0 | 6.3 | 35.8 |
| Network | Wi-Fi | 186 | 27.0 | 4.8 | 40.6 |
| Network | DNS / DHCP | 179 | 51.6 | 4.6 | 45.2 |
| Business Applications | Integration / API Failure | 170 | 34.1 | 4.4 | 49.6 |
| Infrastructure | Server Outage | 169 | 39.9 | 4.4 | 54.0 |
| Network | Firewall Rule Change | 129 | 25.5 | 3.3 | 57.3 |
| Software | Performance Degradation | 128 | 26.2 | 3.3 | 60.7 |
| Hardware | Mobile Device | 122 | 27.1 | 3.2 | 63.8 |
| Infrastructure | Virtualisation | 122 | 36.5 | 3.2 | 67.0 |
| Cloud Services | AWS Resource Issue | 110 | 39.1 | 2.9 | 69.8 |
| Infrastructure | Backup Failure | 108 | 17.3 | 2.8 | 72.6 |
| Software | Application Crash | 100 | 15.4 | 2.6 | 75.2 |
| Access & Identity | SSO Failure | 95 | 26.2 | 2.5 | 77.7 |
| Email & Collaboration | SharePoint / OneDrive | 84 | 10.7 | 2.2 | 79.9 |
| Access & Identity | MFA Issue | 82 | 12.3 | 2.1 | 82.0 |

**5. Business interpretation.** Nineteen of 39 subcategories produce 80% of all SLA breaches. VPN Connectivity is the largest single source (361 breaches, 9.4%). Network subcategories take five of the top ten places, and LAN/Switching and DNS/DHCP breach more than half the time. Azure resource issues and ERP issues complete the top four. A focused improvement programme on these 19 subcategories covers most of the breach volume.

---

## Q31

### Root cause x priority matrix

**1. Business question.** How do incidents and breach rates spread across root causes and priorities?

**2. SQL solution** (`database/queries/07_pareto_root_cause.sql`)

```sql
SELECT root_cause,
       count(*) FILTER (WHERE priority = 'P1') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P1'))::text, '-') || '%)' AS p1,
       count(*) FILTER (WHERE priority = 'P2') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P2'))::text, '-') || '%)' AS p2,
       count(*) FILTER (WHERE priority = 'P3') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P3'))::text, '-') || '%)' AS p3,
       count(*) FILTER (WHERE priority = 'P4') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P4'))::text, '-') || '%)' AS p4,
       count(*)                                                AS total
FROM analytics.fact_tickets
WHERE is_incident AND is_resolved AND root_cause IS NOT NULL
GROUP BY root_cause
ORDER BY total DESC, root_cause;
```

**3. Why this technique.** Conditional aggregation pivot producing "count (breach %)" cells. A matrix view lets a Service Delivery Manager spot combinations, e.g. vendor P1s.

**4. Actual result** - 11 row(s), 50 ms including client round-trip; saved to `database/query_results/Q31.csv`

| root_cause | p1 | p2 | p3 | p4 | total |
|---|---|---|---|---|---|
| Configuration Error | 160 (38%) | 546 (24%) | 1593 (18%) | 836 (10%) | 3135 |
| Change-Related | 181 (48%) | 633 (30%) | 1373 (29%) | 672 (13%) | 2859 |
| User Error | 70 (31%) | 290 (9%) | 1051 (7%) | 720 (2%) | 2131 |
| Hardware Failure | 80 (46%) | 238 (30%) | 772 (28%) | 386 (18%) | 1476 |
| Third-Party / Vendor | 74 (68%) | 278 (48%) | 638 (36%) | 306 (24%) | 1296 |
| Software Defect | 74 (41%) | 257 (25%) | 577 (26%) | 244 (12%) | 1152 |
| Undetermined | 49 (43%) | 160 (27%) | 573 (22%) | 308 (12%) | 1090 |
| Known Error | 60 (48%) | 146 (29%) | 445 (18%) | 262 (8%) | 913 |
| Security Threat | 28 (39%) | 139 (7%) | 429 (5%) | 259 (2%) | 855 |
| Capacity / Performance | 58 (29%) | 160 (28%) | 383 (29%) | 178 (13%) | 779 |
| Network Connectivity | 25 (44%) | 96 (45%) | 221 (33%) | 98 (26%) | 440 |

**5. Business interpretation.** The matrix shows two clear patterns. Third-Party/Vendor issues have the highest breach rate at P1–P3 (68% at P1) and the second-highest at P4 (24%, against 26% for Network Connectivity). User Error and Security Threat incidents rarely breach below P1 (2–9%). Change-related P1s breach 48% of the time. Every root cause breaches far more often at P1 than at P4, which is consistent with P1 targets being far tighter relative to the work involved.

---

## Q32

### Chronic customer problems (repeat incidents)

**1. Business question.** Which customer + subcategory pairs recur most, and what root cause is recorded?

**2. SQL solution** (`database/queries/07_pareto_root_cause.sql`)

```sql
SELECT c.customer_name, f.subcategory,
       count(*)                                                 AS incidents,
       count(*) FILTER (WHERE f.is_repeat_incident)             AS repeat_incidents,
       mode() WITHIN GROUP (ORDER BY f.root_cause)              AS most_common_root_cause,
       round(100 * avg(f.sla_breached::int), 0)                 AS breach_pct,
       min(f.created_date)                                      AS first_seen,
       max(f.created_date)                                      AS last_seen
FROM analytics.fact_tickets f
JOIN analytics.dim_customer c ON c.customer_id = f.customer_id
WHERE f.is_incident AND NOT c.is_placeholder
GROUP BY c.customer_name, f.subcategory
HAVING count(*) FILTER (WHERE f.is_repeat_incident) >= 10
ORDER BY repeat_incidents DESC, incidents DESC, c.customer_name, f.subcategory
LIMIT 15;
```

**3. Why this technique.** GROUP BY two keys, mode() WITHIN GROUP for the most common root cause, HAVING. mode() names the dominant root cause per pair - the input a Problem Manager needs.

**4. Actual result** - 15 row(s), 95 ms including client round-trip; saved to `database/query_results/Q32.csv`

| customer_name | subcategory | incidents | repeat_incidents | most_common_root_cause | breach_pct | first_seen | last_seen |
|---|---|---|---|---|---|---|---|
| Granite Renewables plc | ERP Issue | 98 | 97 | Known Error | 47 | 2024-01-02 | 2025-12-30 |
| Riverside Stores Ltd | ERP Issue | 67 | 60 | Known Error | 37 | 2024-01-03 | 2025-12-30 |
| Linden Plastics Ltd | SharePoint / OneDrive | 63 | 57 | Known Error | 16 | 2024-01-09 | 2025-12-29 |
| Nevis Care Group plc | VPN Connectivity | 43 | 34 | Configuration Error | 12 | 2024-01-17 | 2025-12-23 |
| Yarrow Advisory LLP | Integration / API Failure | 37 | 29 | Known Error | 49 | 2024-04-08 | 2025-12-23 |
| Dunmore Freight plc | Wi-Fi | 37 | 28 | Configuration Error | 19 | 2024-01-11 | 2025-12-28 |
| Wexford Care Group Group | Backup Failure | 37 | 27 | Known Error | 6 | 2024-02-14 | 2025-12-19 |
| Bramley Housing Trust | ERP Issue | 35 | 26 | Known Error | 44 | 2024-01-13 | 2025-12-15 |
| Holloway Distribution Ltd | Wi-Fi | 34 | 26 | Configuration Error | 32 | 2024-02-15 | 2025-12-26 |
| Northgate Care Group Ltd | VPN Connectivity | 30 | 26 | Known Error | 55 | 2024-10-31 | 2025-11-10 |
| Elmstead Home Group | SSO Failure | 34 | 25 | Configuration Error | 52 | 2024-01-15 | 2025-11-26 |
| Clifton College | Backup Failure | 33 | 22 | Configuration Error | 6 | 2024-01-08 | 2025-12-09 |
| Marlow Insurance plc | Backup Failure | 24 | 20 | Configuration Error | 26 | 2024-12-23 | 2025-12-10 |
| Osprey Engineering Group | VPN Connectivity | 25 | 16 | Change-Related | 48 | 2024-01-01 | 2025-12-31 |
| Abbey Distribution Ltd | ERP Issue | 23 | 15 | Known Error | 9 | 2024-01-16 | 2025-12-05 |

**5. Business interpretation.** A small number of customer and subcategory pairs are effectively chronic problems. Granite Renewables plc has 98 ERP incidents, 97 of them repeats. Riverside Stores Ltd (67 ERP incidents) and Linden Plastics Ltd (63 SharePoint/OneDrive incidents) follow. The dominant recorded root cause is Known Error or Configuration Error, meaning the issue is understood but not permanently fixed. Each of the top pairs should get a formal problem record with an owner and a permanent-fix plan. The volume they generate makes this one of the highest-return actions available.

---

## Q33

### At-risk customer list (BR-RULE-14)

**1. Business question.** Which customers meet the at-risk rule in the last 90 days, and why?

**2. SQL solution** (`database/queries/08_customer_team.sql`)

```sql
SELECT customer_name, sla_level, customer_success_manager, resolved_tickets,
       sla_breach_pct_90d, repeat_incident_pct_90d, avg_csat_90d, csat_responses_90d,
       concat_ws('; ',
           CASE WHEN flag_high_breach THEN 'breach rate >= 1.5x company' END,
           CASE WHEN flag_repeat_incidents THEN 'repeat incidents >= 20%' END,
           CASE WHEN flag_low_csat THEN 'CSAT <= 3.5' END)               AS reasons
FROM analytics.customer_risk
WHERE is_at_risk
ORDER BY risk_flags DESC, sla_breach_pct_90d DESC, customer_name;
```

**3. Why this technique.** Read the rule view, build a human-readable reason with CONCAT_WS and CASE. CSMs need the evidence behind each flag, not just a yes/no.

**4. Actual result** - 15 row(s), 64 ms including client round-trip; saved to `database/query_results/Q33.csv`

| customer_name | sla_level | customer_success_manager | resolved_tickets | sla_breach_pct_90d | repeat_incident_pct_90d | avg_csat_90d | csat_responses_90d | reasons |
|---|---|---|---|---|---|---|---|---|
| Clifton Clinics Ltd | Platinum | Owen Bell | 16 | 62.5 | 25.0 | 3.0 | 8 | breach rate >= 1.5x company; repeat incidents >= 20%; CSAT <= 3.5 |
| Cotswold Technologies Ltd | Gold | Kofi Mensah | 25 | 36.0 | 40.9 | 3.4 | 10 | breach rate >= 1.5x company; repeat incidents >= 20%; CSAT <= 3.5 |
| Granite Renewables plc | Platinum | Daniel Price | 24 | 33.3 | 54.2 | 3.46 | 13 | breach rate >= 1.5x company; repeat incidents >= 20%; CSAT <= 3.5 |
| Nevis Manufacturing Ltd | Platinum | Isla Murray | 20 | 60.0 | 23.1 | 3.88 | 8 | breach rate >= 1.5x company; repeat incidents >= 20% |
| Sterling Technologies Ltd | Platinum | Kofi Mensah | 17 | 58.8 | 35.3 | 3.83 | 6 | breach rate >= 1.5x company; repeat incidents >= 20% |
| Northgate Engineering plc | Platinum | Priya Kaur | 29 | 51.7 | 22.6 | 3.53 | 15 | breach rate >= 1.5x company; repeat incidents >= 20% |
| Ullswater Learning | Platinum | Isla Murray | 16 | 50.0 | 7.1 | 3.43 | 7 | breach rate >= 1.5x company; CSAT <= 3.5 |
| Moorland Transport Ltd | Platinum | Daniel Price | 22 | 45.5 | 6.3 | 3.2 | 5 | breach rate >= 1.5x company; CSAT <= 3.5 |
| Derwent Components Ltd | Platinum | Daniel Price | 35 | 42.9 | 19.4 | 3.5 | 18 | breach rate >= 1.5x company; CSAT <= 3.5 |
| Stanmore Labs Group | Platinum | Priya Kaur | 28 | 42.9 | 22.7 | 4.08 | 13 | breach rate >= 1.5x company; repeat incidents >= 20% |
| Holloway Distribution Ltd | Gold | Priya Kaur | 12 | 41.7 | 46.2 | 3.5 | 2 | breach rate >= 1.5x company; repeat incidents >= 20% |
| Tamar Wealth Ltd | Platinum | Daniel Price | 17 | 41.2 | 18.2 | 3.0 | 5 | breach rate >= 1.5x company; CSAT <= 3.5 |
| Cotswold Components Ltd | Platinum | Isla Murray | 25 | 36.0 | 33.3 | 3.5 | 4 | breach rate >= 1.5x company; repeat incidents >= 20% |
| Albion Home Ltd | Gold | Daniel Price | 20 | 30.0 | 31.6 | 3.43 | 7 | repeat incidents >= 20%; CSAT <= 3.5 |
| Riverside Stores Ltd | Platinum | Isla Murray | 14 | 21.4 | 66.7 | 3.33 | 6 | repeat incidents >= 20%; CSAT <= 3.5 |

**5. Business interpretation.** Fifteen customers meet the at-risk rule (BR-RULE-14) in the last 90 days. Twelve are Platinum and three are Gold. Three meet all three criteria: Clifton Clinics Ltd, Cotswold Technologies Ltd and Granite Renewables plc. Clifton Clinics breached 62.5% of the time, with an average CSAT of 3.00. The list names the CSM for each customer. Some CSAT figures rest on few responses (for example, Holloway Distribution has only 2 responses), so the CSAT criterion alone should not be over-weighted. The rule requires at least 5 responses before the CSAT flag can be set.

---

## Q34

### Team scorecard against the company average

**1. Business question.** How does each team compare with the average team on every headline KPI?

**2. SQL solution** (`database/queries/08_customer_team.sql`)

```sql
SELECT team_name, tickets, tickets_per_agent_per_month,
       sla_breach_pct,
       round(sla_breach_pct - avg(sla_breach_pct) OVER (), 1)        AS breach_vs_avg_pp,
       median_resolution_hours,
       fcr_pct,
       round(fcr_pct - avg(fcr_pct) OVER (), 1)                      AS fcr_vs_avg_pp,
       reopen_pct, avg_csat,
       rank() OVER (ORDER BY sla_breach_pct)                         AS sla_rank,
       rank() OVER (ORDER BY avg_csat DESC)                          AS csat_rank
FROM analytics.kpi_team
ORDER BY sla_rank;
```

**3. Why this technique.** AVG() OVER () across the result set for deltas; RANK() for a league position. Window aggregates over the whole result give the benchmark without a second query.

**4. Actual result** - 8 row(s), 136 ms including client round-trip; saved to `database/query_results/Q34.csv`

| team_name | tickets | tickets_per_agent_per_month | sla_breach_pct | breach_vs_avg_pp | median_resolution_hours | fcr_pct | fcr_vs_avg_pp | reopen_pct | avg_csat | sla_rank | csat_rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Service Desk | 4648 | 10.76 | 4.09 | -13.1 | 6.31 | 53.1 | 30.2 | 4.92 | 4.282 | 1 | 1 |
| Security Operations | 1398 | 7.28 | 5.95 | -11.2 | 7.55 | 22.26 | -0.6 | 6.22 | 4.235 | 2 | 2 |
| Database Services | 1118 | 6.65 | 10.87 | -6.3 | 12.11 | 17.71 | -5.2 | 7.18 | 4.091 | 3 | 3 |
| Identity & Access Management | 1861 | 11.08 | 11.45 | -5.7 | 12.27 | 30.86 | 8.0 | 6.78 | 4.07 | 4 | 4 |
| End User Computing | 3621 | 15.09 | 16.17 | -1.0 | 19.46 | 31.74 | 8.9 | 6.81 | 3.999 | 5 | 5 |
| Application Support | 2955 | 10.26 | 25.77 | 8.6 | 18.27 | 7.01 | -15.9 | 10.54 | 3.791 | 6 | 7 |
| Infrastructure & Cloud | 3191 | 12.09 | 27.91 | 10.7 | 21.82 | 9.46 | -13.4 | 7.21 | 3.804 | 7 | 6 |
| Network Operations | 3298 | 19.63 | 35.22 | 18.0 | 29.72 | 10.9 | -12.0 | 7.34 | 3.64 | 8 | 8 |

**5. Business interpretation.** Breach rate and CSAT rank teams almost identically: the top five positions match exactly, and the bottom three differ only by one swap. Breach performance and satisfaction are therefore closely linked. Network Operations is last on breach rate (18.0 points above the team average), median resolution and CSAT, has low FCR, and carries the highest load per agent (19.6 tickets per agent per month). Application Support has the highest reopen rate (10.5%) and the lowest FCR (7.0%), which points to quality-of-fix issues rather than only speed.

---

## Q35

### Do workarounds come back?

**1. Business question.** How does the reopen rate vary by resolution type, and what does a reopen cost in CSAT?

**2. SQL solution** (`database/queries/08_customer_team.sql`)

```sql
SELECT resolution_type,
       count(*)                                                         AS resolved,
       round(100 * avg(is_reopened::int), 1)                            AS reopen_pct,
       round(avg(customer_satisfaction) FILTER (WHERE NOT is_reopened), 2) AS csat_not_reopened,
       round(avg(customer_satisfaction) FILTER (WHERE is_reopened), 2)     AS csat_reopened
FROM analytics.fact_tickets
WHERE is_resolved AND resolution_type IS NOT NULL
GROUP BY resolution_type
HAVING count(*) >= 100
ORDER BY reopen_pct DESC, resolution_type;
```

**3. Why this technique.** GROUP BY with conditional averages; CSAT split by reopened vs not. Links a process choice (workaround vs permanent fix) to rework and customer experience.

**4. Actual result** - 10 row(s), 67 ms including client round-trip; saved to `database/query_results/Q35.csv`

| resolution_type | resolved | reopen_pct | csat_not_reopened | csat_reopened |
|---|---|---|---|---|
| Workaround | 3250 | 16.4 | 3.97 | 2.93 |
| No Fault Found | 914 | 11.7 | 4.07 | 3.05 |
| Permanent Fix | 1817 | 6.7 | 3.86 | 3.15 |
| Threat Contained | 709 | 5.9 | 4.25 | 3.3 |
| Vendor Fix | 1265 | 5.5 | 3.82 | 2.89 |
| Change Rollback | 1516 | 5.0 | 3.92 | 3.0 |
| Configuration Change | 4385 | 5.0 | 4.01 | 3.05 |
| Hardware Replacement | 1201 | 4.8 | 3.89 | 2.92 |
| User Education | 1751 | 4.7 | 4.25 | 3.33 |
| Request Fulfilled | 4755 | 4.3 | 4.26 | 3.45 |

**5. Business interpretation.** Workarounds come back far more often than permanent fixes. 16.4% of workarounds are reopened, against 6.7% of permanent fixes and about 5% for configuration changes. "No Fault Found" is also reopened 11.7% of the time. A reopen costs 0.7–1.0 CSAT points for every resolution type (for example, workarounds score 3.97 when not reopened and 2.93 when reopened). Converting recurring workarounds into permanent fixes through problem management would therefore improve both rework and satisfaction.

---

## Q36

### Knowledge-base use by team

**1. Business question.** How often does each team use the knowledge base, and is KB use associated with better outcomes?

**2. SQL solution** (`database/queries/08_customer_team.sql`)

```sql
SELECT t.team_name,
       round(100 * avg(f.knowledge_base_used::int), 1)                                AS kb_usage_pct,
       round(100 * avg(f.fcr_achieved::int) FILTER (WHERE f.knowledge_base_used), 1)     AS fcr_pct_with_kb,
       round(100 * avg(f.fcr_achieved::int) FILTER (WHERE NOT f.knowledge_base_used), 1) AS fcr_pct_without_kb,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population AND f.knowledge_base_used))::numeric, 1)     AS median_h_with_kb,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population AND NOT f.knowledge_base_used))::numeric, 1) AS median_h_without_kb
FROM analytics.fact_tickets f
JOIN analytics.dim_team t USING (team_id)
GROUP BY t.team_name
ORDER BY kb_usage_pct, t.team_name;
```

**3. Why this technique.** Conditional aggregation by team and KB flag, difference in FCR rates. Identifies teams where KB adoption is low but the association with FCR is strong.

**4. Actual result** - 8 row(s), 93 ms including client round-trip; saved to `database/query_results/Q36.csv`

| team_name | kb_usage_pct | fcr_pct_with_kb | fcr_pct_without_kb | median_h_with_kb | median_h_without_kb |
|---|---|---|---|---|---|
| Application Support | 29.4 | 13.7 | 4.3 | 14.7 | 19.9 |
| Infrastructure & Cloud | 30.6 | 18.8 | 5.4 | 16.6 | 24.0 |
| Network Operations | 31.5 | 23.7 | 5.2 | 19.6 | 34.7 |
| Database Services | 34.0 | 32.6 | 10.3 | 9.0 | 14.2 |
| Security Operations | 37.0 | 34.7 | 14.5 | 5.6 | 8.9 |
| Identity & Access Management | 39.1 | 48.9 | 19.3 | 8.3 | 15.4 |
| End User Computing | 42.3 | 45.4 | 22.0 | 14.2 | 24.0 |
| Service Desk | 72.9 | 59.7 | 34.9 | 5.5 | 9.3 |

**5. Business interpretation.** Knowledge-base use ranges from 29% (Application Support) to 73% (Service Desk). In every team, KB-assisted tickets have higher FCR and lower median resolution. The specialist teams have the lowest KB usage and some of the largest gaps. In Network Operations, the median is 19.6 hours with the KB and 34.7 hours without. This is associational, since simpler issues are more likely to have articles. Still, it makes a reasonable case for **building KB content for Network, Infrastructure and Application issues**.

---

## Q37

### Negative control - is region a real driver?

**1. Business question.** Regions show different breach rates; is that region itself, or just a different mix of teams, priorities and contracts?

**2. SQL solution** (`database/queries/08_customer_team.sql`)

```sql
WITH cell_tp AS (
    SELECT team_id, priority, avg(sla_breached::int) AS rate
    FROM analytics.fact_tickets GROUP BY team_id, priority
), cell_tps AS (
    SELECT team_id, priority, sla_level, avg(sla_breached::int) AS rate
    FROM analytics.fact_tickets GROUP BY team_id, priority, sla_level
)
SELECT f.region,
       count(*) FILTER (WHERE f.in_sla_population)                          AS resolved_in_scope,
       round(100 * avg(f.sla_breached::int), 1)                             AS observed_breach_pct,
       round(avg(f.sla_breached::int) / avg(a.rate) FILTER (WHERE f.in_sla_population), 2)
                                                                            AS obs_to_exp_team_priority,
       round(avg(f.sla_breached::int) / avg(b.rate) FILTER (WHERE f.in_sla_population), 2)
                                                                            AS obs_to_exp_plus_sla_level,
       round(100 * avg(f.sla_breached::int) FILTER (WHERE f.sla_level = 'Platinum'), 1) AS platinum_breach_pct,
       round(100.0 * count(*) FILTER (WHERE f.sla_level = 'Platinum' AND f.in_sla_population)
             / count(*) FILTER (WHERE f.in_sla_population), 1)              AS pct_platinum_tickets
FROM analytics.fact_tickets f
JOIN cell_tp  a USING (team_id, priority)
JOIN cell_tps b USING (team_id, priority, sla_level)
WHERE f.region <> 'Unknown'
GROUP BY f.region
ORDER BY observed_breach_pct DESC;
```

**3. Why this technique.** Indirect standardisation - expected breaches from team x priority x SLA-level rates, two models compared. Observed/expected near 1.0 after adjustment means the raw regional gap is explained by work and contract mix.

**4. Actual result** - 8 row(s), 337 ms including client round-trip; saved to `database/query_results/Q37.csv`

| region | resolved_in_scope | observed_breach_pct | obs_to_exp_team_priority | obs_to_exp_plus_sla_level | platinum_breach_pct | pct_platinum_tickets |
|---|---|---|---|---|---|---|
| London | 4742 | 20.4 | 1.12 | 1.02 | 33.7 | 33.3 |
| Scotland | 2086 | 19.2 | 1.09 | 1.02 | 32.7 | 22.7 |
| South East | 4010 | 18.2 | 0.98 | 1.01 | 34.2 | 22.5 |
| Wales | 1531 | 18.1 | 0.98 | 0.98 | 38.9 | 7.1 |
| South West | 1725 | 18.0 | 1.0 | 1.01 | 33.8 | 25.4 |
| Yorkshire & North East | 2346 | 17.6 | 0.94 | 0.97 | 32.4 | 30.4 |
| Midlands | 2717 | 16.5 | 0.93 | 0.99 | 30.7 | 15.9 |
| North West | 2345 | 15.3 | 0.87 | 0.95 | 31.6 | 17.3 |

**5. Business interpretation.** **Negative control.** In the synthetic generator, region was deliberately given no effect. Raw breach rates vary from 15.3% (North West) to 20.4% (London), which could be misread as regional performance. Adjusting for the team and priority mix narrows the observed-to-expected ratios to 0.87–1.12. Adding the customer's SLA level as well brings every region to 0.95–1.02. London and Scotland simply have more Platinum-contract tickets, and Platinum targets are breached most (Q06). Region is not a driver in this data, and the method correctly avoids a false finding. The same check should be applied before presenting any "regional performance" conclusion.

---
