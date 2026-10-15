# Business interpretations (written after reading the executed results)

These are merged into docs/sql_analysis.md by scripts/run_sql_analysis.py.
They describe the seed-42 dataset. If the data is regenerated with another
seed, re-read the results and update the numbers.

## Q01
97.2% of the 22,090 valid tickets are Closed. The open backlog at the snapshot is 250 tickets (1.1%): 138 In Progress, 77 Pending Customer, 30 On Hold and 5 New. Cancelled tickets (1.25%) are excluded from every SLA and satisfaction KPI. The backlog is small relative to monthly volume, which is about 700–1,150 tickets, so the open-ticket exception list (Q02) is more useful than the backlog count itself.

## Q02
Some high-priority tickets have been open for weeks. A P1 Security Operations ticket is 1,375 hours old against a 4-hour target, and 10 of the 15 rows are Platinum customers. Most of these tickets are "Pending Customer" or "In Progress". Because the SLA clock never pauses (assumption A-03), they count as breaches even when the delay is the customer's. **Action:** a weekly ageing review of open P1/P2 tickets owned by the Service Delivery Manager. Where a contract allows it, the business should also decide whether "Pending Customer" time should pause the clock.

## Q03
Monitoring alerts carry the highest share of high-priority work: 33% of alerts are P1/P2, compared with about 15% for portal, email and chat. Phone is second at 22%, and it carries the most P1s in absolute terms (405). The portal is the largest channel, but its tickets are mostly low priority. 132 tickets have no channel recorded, which is a data-capture gap to raise with the Service Desk.

## Q04
Breach rates vary roughly ninefold between teams. Network Operations breaches 35.2% of the time, followed by Infrastructure & Cloud (27.9%) and Application Support (25.8%). The Service Desk breaches 4.1%. The three worst teams account for 2,742 of the 3,904 breaches (70%). The teams do handle different work, so Q09, Q10 and Q34 separate out the effects of complexity and workload.

## Q05
Five categories breach above the company rate of 18.1%: Network (35.2%), Cloud Services (30.3%), Business Applications (29.6%), Infrastructure (26.2%) and Hardware (19.9%). The first four are the specialist categories handled by the three worst teams in Q04, so category and team effects overlap and should not be read as two separate problems.

## Q06
The tighter the contract, the more often it is breached, even though the work takes about the same time. Median resolution sits between 13 and 18 hours for every SLA level, yet breach rates fall from about 33% (Platinum) to 22% (Gold), 7% (Silver) and 4% (Bronze). The most valuable customers therefore have the worst experience against their contract. The cause is not that their tickets are handled more slowly; the targets are simply stricter. **Implication:** routing should prioritise by SLA level, so Platinum P3s are not queued behind Bronze P3s. Platinum SME (n = 76) is too small a group to read on its own.

## Q07
Junior agents have the slowest median resolution: 20.3 hours, against 9.9 hours for Seniors and 9.3 hours for Leads. They also have the highest reopen rate (9.3%). Their breach rate (18.4%) is no worse than average, though, because Leads and Seniors are assigned more P1/P2 work, and P1/P2 targets are tighter. Leads show the highest escalation rate (26.9%) for the same reason. This is a **confounded comparison**: priority mix differs by experience level. A fair comparison needs to hold priority constant, which is done in the Phase 5 Python analysis.

## Q08
Chat (34%) and phone (31%) have the best first-contact resolution, ahead of portal and email (about 26%). In every channel, tickets where the knowledge base was used reach roughly 2.5–3.5 times the FCR rate of those where it wasn't (for example, chat 52.9% vs 19.4%). This is an association, not proof that the KB *causes* FCR, because simpler issues are both more likely to have an article and easier to fix first time. Monitoring alerts show 0% by definition: there is no customer contact to resolve at.

## Q09
Four teams are slower than the company median of 14.8 hours. Network Operations is 2.0 times slower (29.7 hours), followed by Infrastructure & Cloud (1.47×), End User Computing (1.31×) and Application Support (1.23×). End User Computing is notable because it handles mostly Low/Medium-complexity hardware and software work, yet is still 31% slower than average. That points to capacity rather than complexity, which Q10 tests.

## Q10
Across 64 team-quarters, tickets per agent per month correlates strongly with breach rate (Pearson r = 0.71). Each additional ticket per agent per month is associated with about 1.9 percentage points more breaches. The relationship holds when the Service Desk is excluded (r = 0.76), so it is not driven by that one large, low-breach team. Workload is still confounded with team complexity, so this is evidence for, not proof of, a capacity problem. It does support **rebalancing headcount towards Network Operations and End User Computing**, which carry the highest load per agent.

## Q11
Fifteen customers with at least 10 survey responses score at least 0.5 below their industry average. Pennine Industries Group has the lowest score (2.79 against a manufacturing average of 4.02). Clifton Clinics Ltd (57 responses, 3.23) and Brightwater Advisory plc (44 responses, 3.09) have large samples, so their low scores are reliable signals rather than noise. These customers belong on the Customer Success Manager review list. Clifton Clinics is also flagged by the formal at-risk rule (Q33).

## Q12
Seventeen customers had both a breached P1 and at least three repeat incidents in the last 90 days. Ten of them are Platinum, six are Gold and one is Silver. Granite Renewables plc (13 repeats), Abbey Software Ltd (11) and Ironbridge Bank plc (9) lead the list. A P1 breach on a customer who is already seeing the same problem repeatedly is a strong churn signal, and the list gives each CSM a named action.

## Q13
For P3/P4 tickets handled by business-hours teams, tickets logged out of hours breach 2.7 times as often as tickets logged in hours (31.1% vs 11.7%). The ratio is 1.9 for on-call teams. 24x7 teams show no difference (1.02). The mechanism is queueing: the ticket waits overnight or over the weekend while the SLA clock runs. **Options:** pause the SLA clock outside the customer's contracted hours, or extend triage cover for business-hours teams. Either would remove most of this breach source without any change to how the work itself is done.

## Q14
Within each industry, the top three customers by volume are a mixed group. Many are Platinum customers breaching 27–39% of the time, such as Granite Renewables (220 tickets, 37.3%) and Clifton Clinics (135 tickets, 38.8%). Others are Silver customers breaching around 5–9%. This matches Q06: contract level, not industry, separates the experience of high-volume customers. Account plans for the largest Platinum accounts should be the first priority.

## Q15
Every team's breach rate rose between 2024 and 2025. Network Operations (+11.0 points, to 40.1%) and Infrastructure & Cloud (+9.7, to 32.3%) deteriorated most. Infrastructure & Cloud overtook Application Support for second place. The ranking order barely changed, so the decline is organisation-wide, consistent with volume growth on flat headcount, rather than a single team failing. The dense-rank column groups teams into 5-point bands. It shows Identity & Access Management and Database Services in the same band, so their rank difference is not meaningful.

## Q16
Month-to-month changes are noisy, ranging from −6.9 to +10.7 points, so a single month should never trigger action. The largest jumps line up with the major-incident spikes found in Q23: September 2025 (+10.7 points, the cloud incident), March 2025 (+7.5, the VPN carrier outage) and October 2024 (+5.6, the integration failure). Breach rates also rise in months where volume jumps, such as January 2025, when volume was up 32.9% and breaches rose 6.9 points.

## Q17
Business Applications and Network issues recur fastest. When a customer has one, 36% and 28% of the time respectively the same customer raises the same subcategory again within 30 days, and 14% and 10% within a week. Database and Security issues recur least (13–14% within 30 days). Fast recurrence suggests fixes that are not permanent, such as workarounds and known errors (see Q35). These two categories are the strongest candidates for problem-management investigations.

## Q18
2024 ended with 10,018 tickets and a year-to-date breach rate of 15.3%. 2025 ended with 12,072 tickets (+20.5%) and 20.5%. The 2025 year-to-date line never drops below 18.7%, so the deterioration was present from January rather than building up during the year. This is the headline trend for the Head of IT Operations.

## Q19
Smoothing over three months shows a clear upward trend in breach rate: about 14% through mid-2024, rising to 19–23% through the second half of 2025. Median resolution time rose from about 12–13 hours to 16–18 hours over the same period, and average CSAT drifted down from about 4.05 to 3.90. All three move together, which is consistent with a capacity problem. The first two months have a partial window and are labelled as such.

## Q20
The top quartile of customers by volume (124 customers) generates 58.4% of all tickets and has a repeat-incident rate of 17.8%, about ten times the bottom quartile's 1.8%. Their average breach rate is also the highest (19.6%). Customer success effort should concentrate on this quartile. Problem management for these customers would remove a disproportionate share of total volume.

## Q21
Monday and Tuesday are the busiest days (19.7% and 21.0% of weekly volume), and volume falls through the week to Friday (15.1%). Weekends carry only 8.5% of volume combined. The 08:00–12:00 band is the daily peak on every weekday. About 1,900 weekday tickets arrived after 18:00 over the two years, and these feed the out-of-hours queue described in Q13. Staffing should be weighted towards Monday and Tuesday mornings.

## Q22
Every quarter of 2025 had more tickets than the same quarter of 2024, by 15–27%, and a higher breach rate, by 3.1–8.1 points. CSAT was lower in every quarter as well. Because quarters are compared like for like, seasonality is ruled out: the deterioration is a genuine year-on-year trend.

## Q23
The three days with the highest volume relative to normal are the three major incidents, with no false alarms: 23 September 2025 (Azure resource issue, 3.0 times normal), 11 March 2025 (VPN connectivity, 3.0 times) and 8 October 2024 (integration/API failure, 2.5 times). The next highest day reaches only 1.7 times normal, so a "more than twice normal" threshold separates major incidents cleanly. This could feed an automated major-incident alert.

## Q24
Change-related incidents rose from 13.6% of incidents with a known root cause (Q1 2024) to 23.4% (Q4 2025). They also breach SLA more often than other incidents in every quarter, for example 30.3% vs 22.3% in Q4 2025. Change-related incidents are therefore both growing in number and harder to resolve within target. **Recommendation:** strengthen change management, through change advisory board review of high-risk changes, post-implementation review and better rollback plans, with KPI-15 as the measure of success.

## Q25
Median resolution is broadly within target, but the tails are not. The P1 median is 4.7 hours, so more than half of all P1s take longer than the 4-hour Platinum/Gold target. The P2 90th percentile (25.1 hours) is three times the strictest P2 target of 8 hours. Averages such as the 25.2-hour mean for P3 hide this. SLA reporting should therefore use percentiles alongside breach rates.

## Q26
Close to half of all breaches (45.5%) miss the target by less than 50%, and 28.9% by less than 25%. These near-misses could be recovered by faster triage, or by alerting before a ticket breaches, rather than by deeper technical change. At the other end, 13.4% of breaches overrun by three times the target or more. These are the long-tail cases (vendor dependencies, tickets left open) that need individual review.

## Q27
P1 first response is strong (96.1% within target, median 4 minutes). Performance degrades with priority: P2 87.2%, P3 75.3%. For every priority, email and the portal are the weakest channels. P3 email meets its response target only 62.9% of the time, against 88.3% for phone. Faster acknowledgement of email and portal tickets, for example an automated triage queue, is a low-cost improvement.

## Q28
Escalated tickets take 2.5–4.5 times longer than non-escalated tickets of the same priority. For example, P2 tickets have a median of 13.7 hours when escalated, against 4.3 hours otherwise. Escalated P1s breach 65% of the time, against 15% for non-escalated P1s, and 56% of P1s are escalated. Escalation partly reflects genuinely harder work, so not every escalation can be avoided. The hand-off delay is still worth measuring, and better L1 knowledge-base content could resolve some of these tickets before they need escalating.

## Q29
Three root causes, Configuration Error (19.4%), Change-Related (17.7%) and User Error (13.2%), account for half of all incidents. Seven causes reach 81.5%, so the distribution is flatter than a classic 80/20 pattern. The class-A causes differ greatly in how they perform against SLA. User Error breaches only 6.6% of the time and is cheap to fix through user education and self-service. Change-Related breaches 26.8% and is costly. Third-Party/Vendor issues are the worst-performing high-volume cause (37.8%), which points to supplier SLA management.

## Q30
Nineteen of 39 subcategories produce 80% of all SLA breaches. VPN Connectivity is the largest single source (361 breaches, 9.4%). Network subcategories take five of the top ten places, and LAN/Switching and DNS/DHCP breach more than half the time. Azure resource issues and ERP issues complete the top four. A focused improvement programme on these 19 subcategories covers most of the breach volume.

## Q31
The matrix shows two clear patterns. Third-Party/Vendor issues have the highest breach rate at P1–P3 (68% at P1) and the second-highest at P4 (24%, against 26% for Network Connectivity). User Error and Security Threat incidents rarely breach below P1 (2–9%). Change-related P1s breach 48% of the time. Every root cause breaches far more often at P1 than at P4, which is consistent with P1 targets being far tighter relative to the work involved.

## Q32
A small number of customer and subcategory pairs are effectively chronic problems. Granite Renewables plc has 98 ERP incidents, 97 of them repeats. Riverside Stores Ltd (67 ERP incidents) and Linden Plastics Ltd (63 SharePoint/OneDrive incidents) follow. The dominant recorded root cause is Known Error or Configuration Error, meaning the issue is understood but not permanently fixed. Each of the top pairs should get a formal problem record with an owner and a permanent-fix plan. The volume they generate makes this one of the highest-return actions available.

## Q33
Fifteen customers meet the at-risk rule (BR-RULE-14) in the last 90 days. Twelve are Platinum and three are Gold. Three meet all three criteria: Clifton Clinics Ltd, Cotswold Technologies Ltd and Granite Renewables plc. Clifton Clinics breached 62.5% of the time, with an average CSAT of 3.00. The list names the CSM for each customer. Some CSAT figures rest on few responses (for example, Holloway Distribution has only 2 responses), so the CSAT criterion alone should not be over-weighted. The rule requires at least 5 responses before the CSAT flag can be set.

## Q34
Breach rate and CSAT rank teams almost identically: the top five positions match exactly, and the bottom three differ only by one swap. Breach performance and satisfaction are therefore closely linked. Network Operations is last on breach rate (18.0 points above the team average), median resolution and CSAT, has low FCR, and carries the highest load per agent (19.6 tickets per agent per month). Application Support has the highest reopen rate (10.5%) and the lowest FCR (7.0%), which points to quality-of-fix issues rather than only speed.

## Q35
Workarounds come back far more often than permanent fixes. 16.4% of workarounds are reopened, against 6.7% of permanent fixes and about 5% for configuration changes. "No Fault Found" is also reopened 11.7% of the time. A reopen costs 0.7–1.0 CSAT points for every resolution type (for example, workarounds score 3.97 when not reopened and 2.93 when reopened). Converting recurring workarounds into permanent fixes through problem management would therefore improve both rework and satisfaction.

## Q36
Knowledge-base use ranges from 29% (Application Support) to 73% (Service Desk). In every team, KB-assisted tickets have higher FCR and lower median resolution. The specialist teams have the lowest KB usage and some of the largest gaps. In Network Operations, the median is 19.6 hours with the KB and 34.7 hours without. This is associational, since simpler issues are more likely to have articles. Still, it makes a reasonable case for **building KB content for Network, Infrastructure and Application issues**.

## Q37
**Negative control.** In the synthetic generator, region was deliberately given no effect. Raw breach rates vary from 15.3% (North West) to 20.4% (London), which could be misread as regional performance. Adjusting for the team and priority mix narrows the observed-to-expected ratios to 0.87–1.12. Adding the customer's SLA level as well brings every region to 0.95–1.02. London and Scotland simply have more Platinum-contract tickets, and Platinum targets are breached most (Q06). Region is not a driver in this data, and the method correctly avoids a false finding. The same check should be applied before presenting any "regional performance" conclusion.
