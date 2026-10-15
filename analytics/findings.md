# Interpretations merged into docs/python_analysis_report.md (written after reading the results)

## summary
1. **Service is getting worse at a measurable rate.** The SLA breach rate rises by 0.38 percentage points per month (p < 0.001), from about 14% in early 2024 to 20–23% in late 2025. Over the same period, monthly volume grows by about 13 tickets a month, while headcount is flat. Volume and breach rate move together month by month (Spearman ρ = 0.91).
2. **Team breach gaps survive adjustment for work mix.** After adjusting for priority and contract level, Network Operations breaches 1.87 times as often as its work mix predicts, and Infrastructure & Cloud 1.43 times. The Service Desk and Security Operations come in well below expectation (0.26 and 0.32).
3. **Platinum customers have the worst experience.** They breach 33% of the time, against 4% for Bronze, because their targets are tighter while handling times are similar.
4. **Breaches are strongly associated with lower satisfaction.** Average CSAT is 4.28 when SLA is met and 2.88 when it is breached, a large effect (rank-biserial 0.78).
5. **Recurring problems are concentrated.** A segment of 52 "chronic-problem" accounts has a 28% repeat-incident rate. Two root causes, third-party/vendor issues and change-related incidents, produce the most breaches above what their volume would predict.
6. **A creation-time model can rank breach risk.** On the held-out final six months it reaches ROC-AUC 0.85, against 0.59 for a simple business rule. The top 20% of scored tickets contain 56% of all breaches ([model report](model_report.md)).

## eda
The data covers two full years, with a clear upward volume trend and dips in August and December. There are 500 customer IDs, which includes the Unknown placeholder used for orphan tickets. The numeric columns are heavily right-skewed. For example, the maximum resolution time is far above the 75th percentile, so the analysis relies on medians, percentiles and rank-based tests.

## cleaning
Every cleaning step is logged with a count. The largest corrections are category labels (555 rows), missing root causes (891) and missing knowledge-base flags (669). The pandas pipeline and the SQL pipeline produce identical KPI populations, ticket for ticket, which demonstrates that the business rules are unambiguous enough to implement twice.

## missing
Most missing values are structural, not defects: open tickets have no resolution fields, and most customers don't answer the survey. The important finding is that CSAT is **missing not at random**. 51% of breached tickets receive a survey response, against 40% of tickets that met SLA. Unhappy customers respond more often, so the average CSAT is biased slightly downwards. Response rates should always be reported alongside CSAT.

## outliers
The three methods flag similar numbers of tickets in each priority (for P3: 35 by the Tukey fence, 34 by z-score, 35 by the business rule). The business rule is preferred because it encodes a business meaning, a ticket left open, rather than a purely statistical one. All 83 business-rule outliers breached. Removing them reduces the mean resolution time by 17%, from 32.0 to 26.5 hours, but barely moves the median (14.9 to 14.8 hours). This is why the KPIs exclude business-rule outliers from duration measures but keep them in the breach rate.

## descriptive
Resolution times are approximately log-normal for every priority: raw skewness ranges from 2.3 to 4.7, and log skewness is close to 0. Means sit 20–60% above medians. The median rises about five-fold from P1 to P4, from 4.7 hours to 23.4 hours.

## sla
Team and breach status are strongly associated (χ² = 1,783, p < 0.001; Cramér's V = 0.29, moderate). The confidence intervals separate three groups:
- **High:** Network Operations, Infrastructure & Cloud, Application Support.
- **Middle:** End User Computing.
- **Low:** the other four teams.

By contract, breach rates are Platinum 33.2%, Gold 22.2%, Silver 7.4% and Bronze 3.7%.

## correlation
Breaching correlates most strongly with lower CSAT (ρ = −0.60), longer resolution (+0.43), escalation (+0.31), team load (+0.20) and reopens (+0.19). Knowledge-base use correlates negatively with breaching (−0.16). First response time is unrelated to breaching (ρ ≈ 0): a quick acknowledgement does not prevent a breach, the work after it does. These are associations. In particular, escalation and resolution time are partly two views of the same underlying difficulty.

## pareto
The root-cause distribution is flatter than 80/20: seven of eleven causes are needed to reach 80% of incidents. Volume alone is therefore a weak guide to priorities. Section 9 ranks causes by **excess breaches** instead.

## rca
Ranked by breaches above the company-average rate, third-party/vendor issues (+214 excess breaches) and change-related incidents (+159) are the clearest improvement targets. Next come hardware failure (+77) and network connectivity (+60). Configuration and user errors are high in volume but breach *less* often than average, so they are cheaper problems that self-service and the knowledge base can address.

Escalated tickets have 4.35 times the odds of breaching after stratifying by priority. The effect is present at every priority level. Change-related incidents grow by 1.42 percentage points of share per quarter (p < 0.001).

## teams
Resolution times differ significantly between teams (Kruskal–Wallis H = 3,061, p < 0.001). The adjusted ratios are the fair comparison, because they account for each team's priority and contract mix.
- Network Operations has the highest load (19.6 tickets per agent per month) and the worst adjusted ratio (1.87).
- End User Computing carries the second-highest load (15.1) yet performs exactly as its mix predicts (0.99). Its raw breach rate is not a team-specific problem.
- Across eight teams, load and the adjusted ratio correlate at ρ = 0.67 (p = 0.07). The direction is consistent with a capacity effect, but eight teams is too few for a firm statistical conclusion. The team-quarter analysis in SQL (Q10, r = 0.71 over 64 team-quarters) is stronger evidence.

## segmentation
Four actionable segments emerge. Silhouette scores are modest (0.19–0.24), so these are practical groupings rather than sharply separated clusters.

| Segment | Customers | Profile | Suggested action |
|---|---|---|---|
| **Chronic-problem accounts** | 52 | Median 120 tickets, 28% repeat incidents | Problem management, root-cause fixes |
| **SLA-pressured premium** | 127 | 27% breach rate, CSAT 3.71, 40% Platinum | Priority routing and SLA review |
| **Steady core** | 194 | 7.7% breaches, CSAT 4.21 | Maintain service levels |
| **Low-touch** | 80 | 32% escalation rate on low volume | Check whether escalation is over-used for small accounts |

## timeseries
Three trends are each statistically significant over 24 months:
- **Breach rate:** +0.38 points per month (R² = 0.49).
- **Volume:** +12.8 tickets per month.
- **CSAT:** −0.0074 points per month, about −0.18 points over the two years.

Monthly volume and breach rate are strongly rank-correlated (ρ = 0.91). This supports, but cannot prove, the capacity explanation. Other factors that changed over the same period, such as the rising share of change-related incidents, are confounded with time.
