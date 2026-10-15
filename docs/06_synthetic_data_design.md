# Synthetic data design and assumptions

> Everything in `data/raw/` is synthetic. This document is the "honesty layer". It records which
> patterns were deliberately built into the generator, how they were built, and what conclusions
> the analysis should therefore **not** claim as discoveries.

## 1. Why disclose this

The later phases analyse this data as if it were real, because that is the skill being
demonstrated. Any "finding" is only a rediscovery of a mechanism listed below. In an interview,
the right framing is: *"I designed these mechanisms so there was signal to find. Then I tested
whether my SQL, statistics and model could recover them, and whether they could also avoid
over-claiming about things I didn't build in."*

## 2. Generation pipeline (`scripts/generate_dataset.py`)

1. **Calendar** – 731 days, with England & Wales bank holidays and the UK fiscal year (April start).
2. **Reference tables** – 8 teams, 80 agents, 500 customers, 39 subcategories, and 16 SLA rules.
3. **Daily volume** – Poisson draws around an expected value that combines:
   linear growth (+38% across the period) × day-of-week factor (Mon 1.20 … Sun 0.22) ×
   month seasonality (Aug 0.90, Dec 0.86) × bank holidays (0.30).
4. **Intraday time** – drawn from a business-hours profile on weekdays and a flatter one at weekends.
5. **Customer** – weighted by company size (SME 0.5 … Large Enterprise 3.4) × a random log-normal
   propensity. Only customers whose `customer_since` is on or before the ticket date are eligible.
6. **Subcategory** – a fixed volume mix. Resolver team and complexity come from `incident_categories`.
7. **Three fictional major incidents** – 2024-10-08 (integration failure after a change),
   2025-03-11 (VPN carrier outage) and 2025-09-23 (Azure resource issue). These add 45–85
   tickets each over a few hours.
8. Ticket attributes are then drawn in causal order: priority → channel → team workload →
   agent → KB use → escalation → root cause → FCR → resolution type → timings → reopens → SLA
   breach → status → CSAT.
9. **Data-quality injection** (section 5), logged to `data/reference/dq_injection_log.csv`.

## 3. Built-in relationships (synthetic patterns)

| # | Relationship | Mechanism in the generator | Measured in output (raw, light filtering) |
|---|---|---|---|
| 1 | **Priority → resolution time** | Base hands-on time P1 0.9 h, P2 3.4 h, P3 10.5 h, P4 24 h, × noise | Medians P1 4.8 h … P4 23.6 h |
| 2 | **Complexity / category → breaches** | Complexity multiplier (Low 0.6, Medium 1.0, High 1.55); root-cause multipliers (Third-Party 1.7, Change-Related 1.35) | Network, Infrastructure, Cloud and Business Apps breach far more than Access or Email |
| 3 | **Team workload → performance** | `load_index` = team-month tickets per agent ÷ median. Work time × load^1.15; first response × load^0.8; escalation and FCR probability adjusted. Network Ops (7 agents) and EUC (10) are deliberately under-staffed for their volume | Network Ops breach ≈ 35% vs Service Desk ≈ 4% |
| 4 | **Volume growth + flat headcount → worsening trend** | Growth raises `load_index` over time; no explicit "get worse" term exists | Breach rate 14.2% (2024 H1) → 21.1% (2025 H2) |
| 5 | **Resolution experience → CSAT** | Latent score = 4.45 − 1.10·breach − 0.45·reopens − 0.30·escalated + 0.25·FCR − 0.25·ln(1 + days) + customer effect + noise, rounded to 1–5 | CSAT 4.28 (met SLA) vs 2.87 (breached) |
| 6 | **Repeat incidents ↔ customer** | 30 "problem customers" get 1.8× volume, and 40% of their tickets are forced into one chronic subcategory with root cause Known Error / Configuration Error | 30 customers ≈ 53% of 30-day repeats |
| 7 | **Escalation → delay** | Escalated work × 1.75, plus a 1–6 h hand-off | Median 23.9 h escalated vs 12.5 h not |
| 8 | **Knowledge base → FCR and speed** | KB use: FCR probability +0.22, work time × 0.8 | FCR 41.9% with KB vs 13.2% without |
| 9 | **Experience → speed** | Junior × 1.25, Senior × 0.85, Lead × 0.8; juniors more likely to escalate and cause reopens | Median 20.2 h (Junior) vs 9.9 h (Senior) |
| 10 | **Change-related incidents rising** | Change-Related root-cause weight × (1 + 1.6 × time fraction) | Share 13.7% (2024 Q1) → 23.5% (2025 Q4) |
| 11 | **Out-of-hours queueing** | P3/P4 tickets raised out of hours to business-hours teams wait until 08:00 on the next working day, and the SLA clock keeps running (A-03) | Breach 30.7% out of hours vs 12.9% in hours (P3/P4, business-hours teams) |
| 12 | **Workarounds → reopens** | Reopen rate +0.14 for Workaround, +0.10 for No Fault Found | Visible in the reopen-by-resolution-type analysis |
| 13 | **Outsourced partner agents slower** | Work time × 1.18, escalation +0.06 | Small effect; deliberately weak |
| 14 | **Survey response bias** | Breached tickets are 10 points more likely to receive a survey response | CSAT averages are slightly pessimistic, which is a selection-bias talking point |

### What is NOT built in (so it must not be "found")

- **Region** has no effect on performance. Any regional difference comes from team mix or chance.
- **Industry** has no direct effect. Differences come through company size, SLA level or chronic
  customers.
- **Channel** affects first response and FCR eligibility only. It does not change hands-on work time.
- **Customer success manager** assignment is random. Any CSM "performance" difference is noise.
- **Day-of-week** affects volume only. Monday tickets are not inherently slower, although the
  weekend queue effect (#11) will make Saturday and Sunday tickets *look* slower.

Phase 5 includes at least one check that a non-built-in factor (region) shows no meaningful effect
once team mix is controlled for. This acts as a negative control.

## 4. Status and backlog

- A ticket is **open** if its simulated resolution falls after the snapshot. In addition, a
  decaying share of tickets from the last 60 days (35% at day 0, falling to around 5%) are
  still waiting on a customer or vendor.
- Open tickets have no `resolved_at`, root cause, resolution type, FCR value or CSAT.
- 1.2% of tickets are **Cancelled**. They have no root cause or CSAT.
- 5 tickets are **New**: not yet responded to at the snapshot.

## 5. Injected data-quality issues

| Issue | Rate / count | Detected by | Detection |
|---|---|---|---|
| Inconsistent category labels | 2.5% | V01 | 100% |
| Inconsistent region labels | 0.4% | V04 | 100% |
| Missing root_cause on resolved tickets | 4% | M02 | 100% |
| Missing knowledge_base_used / channel / subcategory / sla_target_hours | 3% / 0.6% / 1% / 0.3% | M03–M06 | 100% |
| Resolved ticket with no agent | 0.4% | R05 | 100% |
| Agent not in ticket's resolver team | 0.5% | R04 | 100% |
| Orphan customer_id | 10 | R01 | 100% |
| Resolution-time outliers (ticket left open 15–45× too long, plus 10–60 days) | 0.35% | O02 | ~95% (see note) |
| resolved_at before created_at | 15 | T03 | 100% |
| first_response_at before created_at | 15 | T04 | 100% |
| first_response_at after resolved_at | 14 | T05 | 100% |
| Closed ticket with no resolved_at | 8 | T01 | 100% |
| CSAT outside 1–5 (0, −1, 6–10) | 0.2% | C01 | 100% |
| FCR = true but escalated / reopened | 33 / 33 | F01 / F02 | 100% |
| P1 with Low business impact | 12 | F03 | 100% |
| Near-duplicate tickets (same issue re-logged 45 s – 15 min later) | 0.6% | D03 | ~98% |
| Exact duplicate rows | 25 | D01 | 100% |
| Missing customer industry / agent shift | 4 / 2 | M01 | 100% (not in answer key) |

Exact figures for the current build are in `data/reports/validation_report.md`.

**Why detection is not always 100%.**

- *Outliers:* injection multiplies the original duration, and the result is capped at the
  snapshot. A few short P1 tickets do not cross "> 30 days or > 10× target" after injection, so
  they are genuinely indistinguishable from a slow ticket. The statistical rule (O01, Tukey fence
  on log hours) is reported alongside the business rule as a cross-check.
- *Near-duplicates:* a duplicate whose `subcategory` was later blanked by the missing-value
  injection cannot match on subcategory. One natural pair also matches by chance; this is a
  genuine false positive, which is realistic.

## 6. Known limitations of the synthetic data

1. **Volume per agent is low.** About 22,000 tickets ÷ 80 agents ÷ 24 months ≈ 12 tickets per agent
   per month. A real L1 service desk would handle many times that. The *ratio* between teams
   is the meaningful signal, because that is what drives the generator's workload effect. Absolute
   productivity numbers should not be quoted as realistic.
2. **The SLA clock does not pause.** Real contracts usually pause for Pending Customer, so the
   breach rates here are higher than a comparable real provider would report.
3. **Single resolver team per ticket.** Re-assignment chains are not modelled; escalation is a flag.
4. **Effects are multiplicative and stationary**, apart from the documented growth and
   change-related trends. Real operations have step changes from re-organisations, tool
   migrations and staff turnover.
5. **CSAT is generated from the ticket's own attributes**, so a model that predicts CSAT from those
   attributes will look better than it would on real data.
6. **Root cause is clean in the generator**, apart from injected gaps. In reality it is among the
   least reliable ITSM fields.

## 7. Reproducibility

- `numpy.random.default_rng(seed)` is the single random source and it is consumed in a fixed order.
- `python scripts/check_reproducibility.py` regenerates the data into a temporary directory and
  compares SHA-256 hashes with `data/raw/manifest.json`.
- A different seed gives different but statistically similar data. Ticket counts vary with the
  Poisson draws, within the ranges in `data/expected_row_counts.json`.
