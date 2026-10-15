# Requirements (Phase 1 baseline)

This is the initial requirements document agreed at the end of Phase 1. Phase 9 extends it into
a full BRD with user stories and Given/When/Then acceptance criteria.

Requirements state **what** is needed. Implementation decisions, which state **how**, are listed
separately in section 5 so the two are not confused.

Priority uses MoSCoW: M = Must, S = Should, C = Could, W = Won't (this release).

## 1. Business requirements

| ID | Requirement | Stakeholder | Objective | Priority |
|---|---|---|---|---|
| BR-01 | Management must be able to see SLA compliance and its trend, overall and by priority, team, category and region. | Head of IT Ops, SDM | OBJ-01 | M |
| BR-02 | The business must be able to identify which root causes and categories account for most incidents and SLA breaches. | SDM, Team Leads | OBJ-03, OBJ-09 | M |
| BR-03 | The business must be able to compare support teams on a consistent, agreed set of KPIs. | Team Leads, Head of IT Ops | OBJ-05, OBJ-10 | M |
| BR-04 | Customer Success must be able to identify customers needing additional support, based on evidence. | CSM | OBJ-11 | M |
| BR-05 | The business must be able to quantify repeat incidents, and the customers and issues that drive them. | SDM, CSM | OBJ-03 | M |
| BR-06 | The business should understand which factors are associated with lower customer satisfaction. | CSM, Head of IT Ops | OBJ-06 | S |
| BR-07 | The business should be able to estimate which open tickets are at risk of breaching SLA. | SDM, Team Leads | OBJ-01 | S |
| BR-08 | KPI definitions must be documented and applied identically in every report. | All | All | M |
| BR-09 | Data-quality issues must be visible and must not silently distort KPIs. | DA, SDM | All | M |

## 2. Functional requirements

| ID | The system shall… | Traces to | Priority |
|---|---|---|---|
| FR-01 | display headline KPIs: total tickets, open tickets, SLA compliance %, breach %, average and median resolution time, FCR %, reopen %, average CSAT | BR-01 | M |
| FR-02 | compare each headline KPI with the equivalent previous period | BR-01 | M |
| FR-03 | show monthly trends for volume, breach rate, resolution time and CSAT | BR-01 | M |
| FR-04 | filter all analytical views by date range, priority, team, category and region | BR-01, BR-03 | M |
| FR-05 | show SLA compliance by priority, category, team and region | BR-01 | M |
| FR-06 | show the distribution of resolution and first-response times | BR-01 | M |
| FR-07 | show a Pareto analysis of incident root causes, with cumulative percentage | BR-02 | M |
| FR-08 | show a root cause × priority matrix of volume and breach rate | BR-02 | S |
| FR-09 | show escalation rate and its association with resolution time | BR-02 | S |
| FR-10 | show a team comparison table with workload, tickets per agent, resolution time, SLA compliance, FCR, reopen rate and CSAT | BR-03 | M |
| FR-11 | list customers ranked by volume, repeat incidents, breach rate and CSAT, with search, sort and pagination | BR-04, BR-05 | M |
| FR-12 | flag at-risk customers using a documented rule (BR-RULE-14) | BR-04 | S |
| FR-13 | provide a paginated, filterable ticket list for drill-down | BR-01 | S |
| FR-14 | report data-quality exceptions and excluded record counts | BR-09 | M |
| FR-15 | show sample size (n) alongside averages where samples can be small | BR-06, BR-09 | M |
| FR-16 | estimate SLA breach risk for tickets, with model performance disclosed | BR-07 | C |
| FR-17 | allow users to edit or close tickets | — | W |

## 3. Non-functional requirements

| ID | Category | Requirement | Priority |
|---|---|---|---|
| NFR-01 | Performance | Dashboard API responses in < 1 s at p95 for the full two-year dataset on a laptop | M |
| NFR-02 | Accuracy | KPI values in the dashboard, Power BI and SQL analysis must agree to 0.1 percentage points | M |
| NFR-03 | Reproducibility | The dataset and all reported numbers can be regenerated from code with a fixed seed | M |
| NFR-04 | Security | No credentials in source code; database access through environment variables; read-only database role for the API | M |
| NFR-05 | Security | All SQL that takes user input is parameterised | M |
| NFR-06 | Usability | Every chart has a title, axis labels and tooltips; colour is never the only carrier of meaning | M |
| NFR-07 | Accessibility | Keyboard-navigable, labelled controls, WCAG 2.1 AA contrast | S |
| NFR-08 | Responsiveness | Usable from 375 px to 1920 px width | S |
| NFR-09 | Reliability | Loading, empty and error states on every data view; the API returns meaningful HTTP status codes | M |
| NFR-10 | Maintainability | Automated tests for API endpoints and KPI calculations; documented project structure | M |
| NFR-11 | Auditability | Every cleaned record traceable to its staging row, with exclusion reasons | M |
| NFR-12 | Privacy | Agent-level data aggregated to team in default views | S |
| NFR-13 | Security | Authentication and role-based access | W (prototype; recorded as a gap) |

## 4. Data requirements

| ID | Requirement |
|---|---|
| DR-01 | Ticket-level data with create, first-response and resolve timestamps, priority, category, team, agent, customer, status, flags, CSAT and root cause |
| DR-02 | Customer, agent, team, SLA rule, category and calendar reference data |
| DR-03 | At least 20,000 tickets covering at least 12 months, to support trends and seasonality |
| DR-04 | Referential integrity between tickets and every reference table, or documented exceptions |

## 5. Implementation decisions (not requirements)

| Decision | Satisfies | Rationale |
|---|---|---|
| PostgreSQL with staging → clean → analytics schemas | BR-08, BR-09, NFR-11 | KPI logic defined once in views; raw data preserved |
| FastAPI backend with psycopg connection pool | FR-01–FR-14, NFR-01, NFR-05 | Typed validation, automatic OpenAPI docs |
| React + TypeScript + Vite + Tailwind + Recharts | FR-01–FR-15, NFR-06–NFR-08 | Common enterprise stack; strong typing of API contracts |
| Power BI star schema on the same analytical views | NFR-02 | Same numbers as the web dashboard |
| Synthetic data generator with an injected-DQ answer key | NFR-03, BR-09 | Reproducible; lets validation be measured |
| Gradient boosting / logistic regression, chronological split | FR-16 | Avoids temporal leakage |
