# KPI catalogue

Each KPI is defined once here and implemented once, in the `analytics` SQL views (Phase 3). The
"Population" column refers to the business rules in `05_business_rules.md`.

| ID | KPI | Definition / formula | Population | Grain | Direction | Target | Owner |
|---|---|---|---|---|---|---|---|
| KPI-01 | Total tickets | `COUNT(DISTINCT ticket_id)` | All valid tickets, excluding duplicates (BR-RULE-01) | Any | — (volume) | — | Head of IT Ops |
| KPI-02 | Open tickets | Count with status in {New, In Progress, Pending Customer, On Hold} at the snapshot | BR-RULE-05 | Snapshot | ↓ | — | SDM |
| KPI-03 | SLA breach rate | Breached ÷ resolved tickets × 100, where breached = `resolution_time_hours > sla_target_hours` | SLA population (BR-RULE-04) | Month, priority, team, category, customer | ↓ | ≤ 15% | SDM |
| KPI-04 | SLA compliance rate | 100 − KPI-03 | SLA population | as above | ↑ | ≥ 85% | SDM |
| KPI-05 | Median resolution time | `PERCENTILE_CONT(0.5)` of `resolution_time_hours` | Resolved, valid timestamps, excl. outliers (BR-RULE-08) | as above | ↓ | ≤ 13 h | Team Leads |
| KPI-06 | Mean resolution time / P90 | Mean and 90th percentile of resolution hours | as KPI-05 | as above | ↓ | — | Team Leads |
| KPI-07 | First-contact resolution rate | Tickets with FCR = true ÷ resolved tickets with FCR recorded × 100 | Resolved; contradictory records excluded (BR-RULE-09) | Team, channel, category | ↑ | ≥ 32% | Team Leads |
| KPI-08 | Reopen rate | Tickets with `reopened_count > 0` ÷ resolved tickets × 100 | Resolved | Team, category, resolution type | ↓ | ≤ 5% | Team Leads |
| KPI-09 | Repeat incident rate | Incidents where the same customer logged the same subcategory within the previous 30 days ÷ incidents × 100 | Incidents only, excl. service requests (BR-RULE-10) | Customer, subcategory, month | ↓ | ≤ 8% | SDM / Problem Mgr |
| KPI-10 | Average CSAT | Mean of `customer_satisfaction` (1–5) | Valid responses only (BR-RULE-07) | Team, customer, month | ↑ | ≥ 4.10 | CSM |
| KPI-11 | CSAT response rate | Tickets with a valid CSAT ÷ resolved tickets × 100 | Resolved | Month | ↑ | ≥ 50% | CSM |
| KPI-12 | Escalation rate | Escalated ÷ all valid tickets × 100 | Valid tickets | Team, priority, category | ↓ (context-dependent) | Monitor | Team Leads |
| KPI-13 | Workload per agent & spread | Tickets ÷ planned headcount ÷ months; spread = max ÷ min across teams | Valid tickets | Team, month | Spread ↓ | ≤ 1.5× | Head of IT Ops |
| KPI-14 | First-response SLA compliance | Share with `first_response_time_hours ≤ response_target_hours` | Tickets with a valid first response | Priority, team, channel | ↑ | ≥ 90% | SDM |
| KPI-15 | Change-related incident share | Incidents with root cause "Change-Related" ÷ incidents with a known root cause × 100 | Incidents, root cause known | Month, category | ↓ | ≤ 10% | Head of IT Ops |
| KPI-16 | At-risk customers | Count of customers meeting BR-RULE-14 | Active customers | Month | ↓ | Reviewed 100% | CSM |
| KPI-17 | Knowledge base usage rate | Tickets with KB used ÷ tickets with KB recorded × 100 | Valid tickets | Team | ↑ | Monitor | Team Leads |
| KPI-18 | Backlog age | Age in hours of open tickets at snapshot; count already past SLA target | Open tickets | Team, priority | ↓ | — | SDM |
| KPI-19 | Data-quality exception rate | Tickets with ≥ 1 DQ flag ÷ all raw rows × 100 | Raw rows | Check | ↓ | Monitor | DA |

## Notes on interpretation

- **Rates always show their denominator (n).** A team with 40 tickets and a 20% breach rate is not
  directly comparable to one with 4,000.
- **Median over mean for resolution time.** Resolution times are right-skewed (log-normal shape), so
  the mean is pulled up by a long tail. Both are reported; targets use the median.
- **Escalation is not inherently bad.** Escalating a P1 to a specialist quickly is correct practice.
  The KPI is therefore monitored rather than targeted.
- **Previous-period comparison** (FR-02) means the same-length window immediately before the
  selected range. Year-on-year comparison is also offered where at least 13 months are in range.
