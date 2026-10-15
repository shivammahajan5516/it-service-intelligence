# Root cause findings and recommendations

> **Synthetic data.** Northbridge Managed Services Ltd is fictional. The findings are what the
> analysis recovers from generated data, and `06_synthetic_data_design.md` lists which patterns were
> built in deliberately. Statistical associations are reported as associations; where a cause is
> suggested, the supporting evidence is cited.

**For:** Head of IT Operations, Service Delivery Manager, Customer Success, Team Leads.
**Period:** January 2024 – December 2025, with H2 2025 as the baseline.

## Summary

Service has deteriorated steadily rather than suddenly. The SLA breach rate rose from 14.6% in
H1 2024 to 21.5% in H2 2025, by about 0.4 percentage points a month. The rise tracks ticket volume
(+20% year on year with flat headcount) and is concentrated in three specialist teams. It falls
hardest on Platinum customers, whose targets are tightest. Because CSAT falls sharply when an SLA
is breached, these problems feed directly into customer satisfaction.

Most of the levers are operational and inexpensive:
- route work by time-to-breach rather than arrival order
- warn before a ticket breaches
- fix the overnight queue
- turn recurring workarounds into permanent fixes

## Findings

| # | Finding | Evidence | Strength |
|---|---|---|---|
| F1 | **Breaches rise with workload.** Across 64 team-quarters, tickets per agent correlates with breach rate (r = 0.71); each extra ticket per agent per month is associated with about +1.9 breach points. Monthly volume and breach rate move together (ρ = 0.91). | SQL Q10, Q18, Q22; Python §12 | Strong association; confounded with time |
| F2 | **Three teams account for 70% of breaches.** Network Operations (35.2%), Infrastructure & Cloud (27.9%) and Application Support (25.8%). After adjusting for priority and contract mix, Network Ops breaches 1.87 times its expected rate and Infrastructure & Cloud 1.43 times. Network Ops also has the highest load (19.6 tickets per agent per month, 2.95 times the lowest team). | Q04, Q09, Q34; Python §10 | Strong |
| F3 | **Platinum customers have the worst experience.** They breach 33.2% of the time against 3.7% for Bronze, although median handling time is similar (13–18 h for every level). Queues are not ordered by contract tightness. | Q06, Q14; Python §6 | Strong |
| F4 | **The overnight queue causes breaches.** P3/P4 tickets logged out of hours to business-hours teams breach 2.7 times as often (31.1% vs 11.7%); 24×7 teams show no gap. | Q13 | Strong (mechanism is clear) |
| F5 | **Many breaches are near-misses.** 45.5% of breaches overrun the target by less than 50%. | Q26 | Strong |
| F6 | **Vendor and change-related incidents drive excess breaches.** Third-party/vendor incidents breach 37.8% of the time (+214 breaches above the company rate). Change-related incidents breach 26.8% (+159), and their share grew from 13.6% to 23.4% of incidents, about +1.4 points per quarter (p < 0.001). | Q24, Q29, Q31; Python §9 | Strong |
| F7 | **Recurring problems are concentrated.** 13.2% of incidents in H2 2025 are 30-day repeats; 30 customers generate 52.8% of all repeats. The largest pairs are effectively chronic: Granite Renewables has 98 ERP incidents, 97 of them repeats. The dominant root causes are Known Error and Configuration Error. | Q17, Q20, Q32; Python §11 | Strong |
| F8 | **Workarounds come back.** 16.4% of workarounds are reopened, against 6.7% of permanent fixes, and a reopen costs 0.7–1.0 CSAT points. | Q35 | Strong |
| F9 | **Breaches cost satisfaction.** CSAT averages 4.28 when the SLA is met and 2.88 when it is breached (rank-biserial effect 0.78). CSAT and breach rank teams almost identically. | Q34; Python §7 | Strong association |
| F10 | **Knowledge-base use is associated with first-contact resolution.** FCR is 2.5–3.5 times higher when the KB is used, in every channel. Specialist teams use the KB least (29–32%). | Q08, Q36 | Association only: simpler issues are likelier to have articles |
| F11 | **Escalation is slow.** Escalated tickets take 2.5–4.5 times longer at the same priority; escalated P1s breach 65% of the time. | Q28; Python §9 (Mantel–Haenszel OR 4.35) | Strong association; partly reflects harder work |
| F12 | **Region is not a driver.** Raw regional gaps (15.3–20.4%) disappear after adjusting for team, priority and contract mix (observed/expected 0.95–1.02). | Q37 | Strong negative result: prevents a false conclusion |

## Recommendations

Each recommendation is linked to the evidence, an owner, the KPI that measures it, and an
indicative effect. The **effects are illustrative upper bounds** from the synthetic data. They
overlap with each other and must not be added together; they show the order of magnitude to expect.

| # | Recommendation | Addresses | Owner | KPI | Indicative effect |
|---|---|---|---|---|---|
| R1 | **Order queues by time remaining to breach**, not arrival time, so Platinum and Gold tickets surface first | F3, F5 | SDM + Team Leads | KPI-03 by SLA level | Part of the gap between Platinum (33%) and Bronze (4%) breach rates |
| R2 | **Pre-breach alert at 75% of target**, with Team Lead swarm or reprioritisation, using the creation-time risk score to flag high-risk tickets at logging (the top 20% of scores contain 56% of breaches) | F5 | Team Leads | KPI-03 | Up to 1,777 near-miss breaches (45.5%) are within reach of a small speed-up |
| R3 | **Fix the overnight queue**: out-of-hours triage cover for business-hours teams, or align the SLA clock with contracted hours where contracts allow | F4 | Head of IT Ops | Out-of-hours breach rate | About 420 breaches (≈ 2 points of the overall rate) over the period |
| R4 | **Rebalance capacity towards Network Operations and Infrastructure & Cloud** (hire, cross-skill, or move low-complexity network work to the Service Desk) | F1, F2 | Head of IT Ops | KPI-13 spread ≤ 1.5×; team O/E ratio → 1.0 | If the three teams performed as their work mix predicts: about 890 fewer breaches (18.2% → about 14.0%) |
| R5 | **Problem management for the top 30 repeat customers**: a problem record, owner and permanent-fix date for every customer–issue pair with 10 or more repeats; a monthly review | F7, F8 | Problem Manager + CSMs | KPI-09 repeat rate ≤ 8% | In 2025, 644 of 1,258 repeat incidents came from these 30 customers |
| R6 | **Strengthen change control**: risk-based CAB review, post-implementation review of every change-related incident, tested rollback plans | F6 | Change Manager | KPI-15 ≤ 10% | Reverses a +1.4 pt/quarter trend; up to 159 excess breaches |
| R7 | **Supplier SLA management**: vendor escalation paths and back-to-back SLAs for the top vendor-dependent subcategories | F6 | SDM / Procurement | Vendor breach rate | Up to 214 excess breaches |
| R8 | **Build KB content for Network, Infrastructure and Application issues**, and suggest articles at logging | F10, F11 | Team Leads | KPI-07 FCR ≥ 32%, KPI-17 | To be validated with an A/B pilot, because the association is not proof of cause |
| R9 | **Make root cause and KB use mandatory at closure**, with a monthly QA sample of 20 tickets per team | DQ assessment | Team Leads | Root-cause completeness | 891 resolved tickets currently lack a root cause |
| R10 | **Monthly at-risk customer review** using BR-RULE-14 (15 customers flagged now; 12 are Platinum) | F3, F7, F9 | CSMs | KPI-16 reviewed 100% | Retention protection for the highest-value contracts |
| R11 | **Raise the survey response rate** (in-ticket one-click survey) and always report CSAT with its response count | F9, CSAT bias | CSM | KPI-11 ≥ 50% | More reliable CSAT; removes the bias towards unhappy responders |

## Suggested sequencing

| Horizon | Actions |
|---|---|
| **0–30 days** | R2 pre-breach alert, R9 mandatory fields, R10 first at-risk review, R1 queue ordering pilot in Network Ops |
| **30–90 days** | R3 overnight triage, R5 problem records for the top 30, R6 CAB changes, R11 survey change |
| **90–180 days** | R4 capacity rebalancing, R7 supplier SLAs, R8 KB programme (A/B pilot first) |

## How success will be measured

Use the dashboard's Executive overview, with H2 2026 compared against H2 2025:
- breach rate ≤ 15%
- median resolution ≤ 13 hours
- repeat rate ≤ 8%
- FCR ≥ 32%
- workload spread ≤ 1.5×
- CSAT ≥ 4.10

Before declaring success, check the following:
- **Volume:** confirm that volume did not simply fall.
- **Reopen rate:** check it has not risen, which would signal premature closure.
- **Adjusted team ratios:** re-run the work-mix adjustment (Python §10) so that a change in work
  mix is not mistaken for improvement.
