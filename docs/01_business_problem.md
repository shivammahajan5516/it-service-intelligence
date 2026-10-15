# Phase 1 – Business problem definition

> **Synthetic scenario.** Northbridge Managed Services Ltd and all of its customers, staff and
> tickets are fictional. The numbers below are measured from the generated dataset
> (`data/reports/baseline_kpis.json`), not invented.

## 1. Company context

**Northbridge Managed Services Ltd** is a fictional UK managed IT services provider headquartered in
London, with delivery hubs in Manchester, Glasgow and Bristol. It supports around 500 business
customers, from SMEs to large enterprises, across financial services, healthcare, retail,
manufacturing, the public sector and other industries.

| Item | Value |
|---|---|
| Customers | 500 (Platinum / Gold / Silver / Bronze SLA levels) |
| Support teams | 8 resolver groups (L1 Service Desk through L3 specialist teams) |
| Agents | 80 |
| Ticket volume | ~22,000 tickets, January 2024 – December 2025 |
| Channels | Self-service portal, email, phone, chat, automated monitoring alerts |
| Contract model | Fully Managed, Co-Managed, Ad-hoc Support |

Ticket volume grew by roughly a third between early 2024 and late 2025, driven by customer
onboarding and wider service scope. Headcount stayed flat over the same period.

## 2. Problem statements

Management has raised ten concerns. Each has been restated as a measurable question, along with
its baseline from the data.

| # | Management concern | Measurable question | Baseline (measured) |
|---|---|---|---|
| P1 | Increasing SLA breaches | What share of resolved tickets miss their resolution target, and how is it trending? | 14.6% (2024 H1) → **21.5%** (2025 H2) |
| P2 | Long resolution times | What is the median resolution time, by priority and team? | Median 12.6 h → **16.9 h** |
| P3 | Repeated incidents | What share of incidents recur for the same customer and subcategory within 30 days? | 11.1% → **13.2%**; 30 customers generate 52.8% of all repeats |
| P4 | Poor first-contact resolution | What share of tickets are resolved at first contact, without escalation or reopening? | 27.0% → **23.9%** |
| P5 | Uneven workload | How do tickets per agent differ between teams? | 6.7 to 19.6 tickets/agent/month (**2.95×** spread) |
| P6 | Declining satisfaction | How is average CSAT (1–5) changing, and what drives it? | 4.03 → **3.90** |
| P7 | Unclear root causes | Which root causes account for most incidents, and are any growing? | Top 3 causes = 50% of incidents; change-related rose from 13.6% to 23.4% per quarter |
| P8 | Limited team visibility | Is there a consistent, comparable scorecard per team? | None exists (manual spreadsheets) |
| P9 | At-risk customers not identified | Which customers combine high volume, repeat incidents, breaches and low CSAT? | No systematic view |
| P10 | Ineffective resource allocation | Does breach rate rise with team workload? | Team breach rates range 4.1% (Service Desk) to 35.2% (Network Ops) |

Baselines are measured on the PostgreSQL clean layer (`analytics.fact_tickets`), after the
business rules in `05_business_rules.md` were applied. The preliminary figures in
`data/reports/baseline_kpis.json` came from a lighter pre-clean and differ by up to 0.7 points.
For example, the H2 2025 breach rate was 21.1% before cleaning and is 21.5% after.

## 3. Business objectives (SMART)

The baseline period is **H2 2025** and the target period is **H2 2026**, unless stated otherwise.

| ID | Objective | KPI | Baseline | Target |
|---|---|---|---|---|
| OBJ-01 | Reduce SLA breaches to 2024 levels | KPI-03 SLA breach rate | 21.5% | ≤ 15.0% |
| OBJ-02 | Shorten resolution times | KPI-05 Median resolution time | 16.9 h | ≤ 13.0 h |
| OBJ-03 | Cut repeat incidents through problem management on the top 30 repeat customers | KPI-09 Repeat incident rate | 13.2% | ≤ 8.0% |
| OBJ-04 | Raise first-contact resolution | KPI-07 FCR rate | 23.9% | ≥ 32.0% |
| OBJ-05 | Rebalance workload across teams | KPI-13 Workload spread (max/min tickets per agent) | 2.95× | ≤ 1.5× |
| OBJ-06 | Recover customer satisfaction | KPI-10 Average CSAT | 3.90 | ≥ 4.10 |
| OBJ-07 | Increase CSAT survey response so the measure is reliable | KPI-11 CSAT response rate | 42.2% | ≥ 50% |
| OBJ-08 | Reduce reopened tickets | KPI-08 Reopen rate | 7.5% | ≤ 5.0% |
| OBJ-09 | Reduce change-related incidents | KPI-15 Change-related incident share | 22.4% | ≤ 10% |
| OBJ-10 | Give every team lead a weekly scorecard | Scorecard availability | 0 of 8 teams | 8 of 8 teams by end Q1 2026 |
| OBJ-11 | Review at-risk customers every month | KPI-16 At-risk customers reviewed by a CSM | Not tracked | 100% monthly |

The analytics platform does not deliver these outcomes by itself. It **measures** them and shows
**where to act**. Achieving the targets depends on operational change, as set out in the Phase 9
recommendations.

## 4. Scope

**In scope**

- Incident and service-request tickets for January 2024 – December 2025, as extracted at
  31-12-2025 23:59.
- SLA monitoring against resolution targets, with first-response targets as a secondary measure.
- Root-cause, repeat-incident, escalation and reopen analysis.
- Team and customer performance views.
- An exploratory SLA-breach risk model.
- A web dashboard (React + FastAPI + PostgreSQL), a Power BI model specification, and supporting
  BA documentation.

**Out of scope**

- Real-time ingestion from an ITSM tool such as ServiceNow or Jira Service Management. The data is
  a batch extract.
- Agent-level performance management decisions. Agent data is aggregated to team level in the
  dashboard, and agent detail is restricted.
- Financial modelling of SLA penalties and contract revenue.
- Business-hours SLA calendars and SLA clock pausing (see assumption A-03).
- Change, problem and asset management records. Root cause is taken from the ticket's own field.
- Authentication and role-based access in the web application. This is a prototype and is noted
  as a non-functional gap.

## 5. Assumptions

| ID | Assumption |
|---|---|
| A-01 | The ticket extract is complete for the period. Tickets are not purged after closure. |
| A-02 | `sla_target_hours` on a ticket is the resolution target. When it is missing it can be re-derived from `sla_targets` using the customer's SLA level and the ticket priority. |
| A-03 | The SLA clock runs in **elapsed calendar hours** from `created_at` to `resolved_at`, with no pausing for "Pending Customer". This is stricter than many real contracts, and it is consistent across all customers. |
| A-04 | `team_id` is the resolver group at closure. Escalation is captured by `escalation_flag`, not by a change of team. |
| A-05 | CSAT is a 1–5 survey sent at resolution. Non-response is normal and is not treated as a defect. |
| A-06 | Timestamps are UK local time (Europe/London). Daylight-saving transitions are not adjusted. |
| A-07 | Root cause is recorded by the resolving agent and may be biased. "Undetermined" is a legitimate value. |
| A-08 | Planned headcount per team is constant over the period. No attrition or hiring data is available. |
| A-09 | Ticket volume per agent is lower than a real service desk would see. Relative workload between teams is meaningful; absolute productivity figures are not (see `docs/06_synthetic_data_design.md`). |

## 6. Constraints

- The data is a single synthetic batch extract, so external validity is limited.
- Stakeholders need outputs they can read without SQL knowledge.
- The solution must run locally on open-source tooling (PostgreSQL, Python, Node), with Power BI
  Desktop as an optional extra.
- No personal data. Agent and customer names are fictional.
