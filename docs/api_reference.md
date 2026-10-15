# API reference

FastAPI service in `backend/`. Interactive docs when running: <http://localhost:8000/docs> (Swagger) and `/redoc`. **All data is synthetic.**

## Conventions

- **Base URL:** `http://localhost:8000`. All endpoints are `GET` and read-only.
- **Common filters** (every dashboard endpoint): `start_date`, `end_date` (YYYY-MM-DD, inclusive), `priority` (P1-P4), `team` (T01-T08), `category`, `region`. Lists can be repeated (`?team=T01&team=T03`) or comma-separated (`?team=T01,T03`).
- **Validation:** invalid input returns **422** with `{"detail": "..."}` (unknown priority, bad date, start after end, unknown category/region, page_size > 100, sort column not allowed).
- **Errors:** database problems return **503** with a generic message (details are logged server-side only). Unknown routes return 404.
- **Security:** parameterised SQL only; sort columns from a whitelist; the API connects as the read-only role `itsi_app` in read-only transactions with a statement timeout; credentials from environment variables; CORS restricted to `API_CORS_ORIGINS`.
- **Previous period** = the same number of days immediately before `start_date` (e.g. 2025-07-01..2025-12-31, 184 days -> 2024-12-29..2025-06-30).
- **Every response** includes an `x-request-id` header; each request is logged with method, path, status and duration.

Examples below are real responses from the seed-42 database (long lists trimmed to 3 items).

## `GET /api/health`

Liveness + database check. 200 when the database answers, 503 otherwise.

Example: `/api/health`

```json
{
  "status": "ok",
  "database": "ok",
  "tickets": 22090
}
```

## `GET /api/meta`

Filter options (teams, categories, regions) and the data range. Cached per process.

Example: `/api/meta`

```json
{
  "teams": [
    {
      "team_id": "T01",
      "team_name": "Service Desk",
      "support_tier": "L1",
      "planned_headcount": 18
    },
    {
      "team_id": "T02",
      "team_name": "End User Computing",
      "support_tier": "L2",
      "planned_headcount": 10
    },
    {
      "team_id": "T03",
      "team_name": "Network Operations",
      "support_tier": "L2/L3",
      "planned_headcount": 7
    },
    "... (5 more)"
  ],
  "priorities": [
    "P1",
    "P2",
    "P3",
    "... (1 more)"
  ],
  "categories": [
    "Access & Identity",
    "Business Applications",
    "Cloud Services",
    "... (7 more)"
  ],
  "regions": [
    "London",
    "Midlands",
    "North West",
    "... (5 more)"
  ],
  "min_date": "2024-01-01",
  "max_date": "2025-12-31",
  "snapshot_at": "2025-12-31 23:59:59",
  "synthetic_data": true
}
```

## `GET /api/overview`

Headline KPIs for the filtered period, the same KPIs for the equal-length previous period, the difference, and the monthly series.

Example: `/api/overview?start_date=2025-07-01&end_date=2025-12-31`

```json
{
  "filters": {
    "start_date": "2025-07-01",
    "end_date": "2025-12-31",
    "priority": [],
    "team": [],
    "category": [],
    "region": []
  },
  "current": {
    "total_tickets": 6227,
    "open_tickets": 250,
    "resolved_tickets": 5902,
    "sla_population": 5880,
    "sla_compliance_pct": 78.47,
    "sla_breach_pct": 21.53,
    "avg_resolution_hours": 29.73,
    "median_resolution_hours": 16.89,
    "fcr_pct": 23.87,
    "reopen_pct": 7.52,
    "escalation_pct": 23.09,
    "avg_csat": 3.9,
    "csat_responses": 2493,
    "repeat_incident_pct": 13.18
  },
  "previous": {
    "total_tickets": 5923,
    "open_tickets": 0,
    "resolved_tickets": 5851,
    "sla_population": 5839,
    "sla_compliance_pct": 80.53,
    "sla_breach_pct": 19.47,
    "avg_resolution_hours": 27.58,
    "median_resolution_hours": 15.59,
    "fcr_pct": 25.12,
    "reopen_pct": 6.9,
    "escalation_pct": 21.75,
    "avg_csat": 3.94,
    "csat_responses": 2440,
    "repeat_incident_pct": 13.8
  },
  "change": {
    "total_tickets": 304,
    "open_tickets": 250,
    "resolved_tickets": 51,
    "sla_population": 41,
    "sla_compliance_pct": -2.06,
    "sla_breach_pct": 2.06,
    "avg_resolution_hours": 2.15,
    "median_resolution_hours": 1.3,
    "fcr_pct": -1.25,
    "reopen_pct": 0.62,
    "escalation_pct": 1.34,
    "avg_csat": -0.04,
    "csat_responses": 53,
    "repeat_incident_pct": -0.62
  },
  "previous_period": {
    "start_date": "2024-12-29",
    "end_date": "2025-06-30"
  },
  "monthly": [
    {
      "month": "2025-07",
      "tickets": 1021,
      "resolved": 1011,
      "sla_breach_pct": 20.73,
      "sla_compliance_pct": 79.27,
      "median_resolution_hours": 17.25,
      "fcr_pct": 22.76,
      "reopen_pct": 8.31,
      "escalation_pct": 24.78,
      "avg_csat": 3.91,
      "csat_responses": 424
    },
    {
      "month": "2025-08",
      "tickets": 861,
      "resolved": 844,
      "sla_breach_pct": 16.57,
      "sla_compliance_pct": 83.43,
      "median_resolution_hours": 13.08,
      "fcr_pct": 23.54,
      "reopen_pct": 6.75,
      "escalation_pct": 21.02,
      "avg_csat": 4.06,
      "csat_responses": 367
    },
    {
      "month": "2025-09",
      "tickets": 1157,
      "resolved": 1149,
      "sla_breach_pct": 27.3,
      "sla_compliance_pct": 72.7,
      "median_resolution_hours": 18.43,
      "fcr_pct": 23.58,
      "reopen_pct": 7.14,
      "escalation_pct": 26.1,
      "avg_csat": 3.76,
      "csat_responses": 472
    },
    "... (3 more)"
  ]
}
```

## `GET /api/trends`

Monthly KPI series.

Example: `/api/trends?start_date=2025-07-01&end_date=2025-12-31&team=T03`

```json
{
  "filters": {
    "start_date": "2025-07-01",
    "end_date": "2025-12-31",
    "priority": [],
    "team": [
      "T03"
    ],
    "category": [],
    "region": []
  },
  "monthly": [
    {
      "month": "2025-07",
      "tickets": 145,
      "resolved": 144,
      "sla_breach_pct": 40.28,
      "sla_compliance_pct": 59.72,
      "median_resolution_hours": 34.44,
      "fcr_pct": 6.94,
      "reopen_pct": 5.56,
      "escalation_pct": 32.41,
      "avg_csat": 3.57,
      "csat_responses": 65
    },
    {
      "month": "2025-08",
      "tickets": 126,
      "resolved": 121,
      "sla_breach_pct": 33.61,
      "sla_compliance_pct": 66.39,
      "median_resolution_hours": 38.43,
      "fcr_pct": 7.44,
      "reopen_pct": 5.79,
      "escalation_pct": 20.63,
      "avg_csat": 3.58,
      "csat_responses": 40
    },
    {
      "month": "2025-09",
      "tickets": 145,
      "resolved": 145,
      "sla_breach_pct": 41.96,
      "sla_compliance_pct": 58.04,
      "median_resolution_hours": 31.81,
      "fcr_pct": 10.34,
      "reopen_pct": 5.52,
      "escalation_pct": 26.21,
      "avg_csat": 3.5,
      "csat_responses": 58
    },
    "... (3 more)"
  ]
}
```

## `GET /api/sla-performance`

Compliance by priority / category / team / region, resolution-time distribution, first response by channel, monthly breach trend per priority.

Example: `/api/sla-performance?start_date=2025-07-01&end_date=2025-12-31`

```json
{
  "filters": {
    "start_date": "2025-07-01",
    "end_date": "2025-12-31",
    "priority": [],
    "team": [],
    "category": [],
    "region": []
  },
  "by_priority": [
    {
      "priority": "P1",
      "tickets": 261,
      "sla_population": 244,
      "sla_compliance_pct": 51.64,
      "sla_breach_pct": 48.36,
      "response_met_pct": 95.79,
      "median_resolution_hours": 5.38,
      "p90_resolution_hours": 11.57
    },
    {
      "priority": "P2",
      "tickets": 980,
      "sla_population": 924,
      "sla_compliance_pct": 69.26,
      "sla_breach_pct": 30.74,
      "response_met_pct": 86.2,
      "median_resolution_hours": 8.52,
      "p90_resolution_hours": 27.8
    },
    {
      "priority": "P3",
      "tickets": 2915,
      "sla_population": 2754,
      "sla_compliance_pct": 76.47,
      "sla_breach_pct": 23.53,
      "response_met_pct": 73.66,
      "median_resolution_hours": 19.43,
      "p90_resolution_hours": 64.18
    },
    "... (1 more)"
  ],
  "by_category": [
    {
      "category": "Network",
      "sla_population": 854,
      "breaches": 344,
      "sla_breach_pct": 40.28
    },
    {
      "category": "Cloud Services",
      "sla_population": 410,
      "breaches": 167,
      "sla_breach_pct": 40.73
    },
    {
      "category": "Infrastructure",
      "sla_population": 483,
      "breaches": 161,
      "sla_breach_pct": 33.33
    },
    "... (7 more)"
  ],
  "by_team": [
    {
      "team_id": "T03",
      "team_name": "Network Operations",
      "sla_population": 854,
      "breaches": 344,
      "sla_compliance_pct": 59.72,
      "sla_breach_pct": 40.28
    },
    {
      "team_id": "T04",
      "team_name": "Infrastructure & Cloud",
      "sla_population": 893,
      "breaches": 328,
      "sla_compliance_pct": 63.27,
      "sla_breach_pct": 36.73
    },
    {
      "team_id": "T05",
      "team_name": "Application Support",
      "sla_population": 760,
      "breaches": 195,
      "sla_compliance_pct": 74.34,
      "sla_breach_pct": 25.66
    },
    "... (5 more)"
  ],
  "by_region": [
    {
      "region": "London",
      "sla_population": 1358,
      "sla_breach_pct": 26.07
    },
    {
      "region": "Midlands",
      "sla_population": 787,
      "sla_breach_pct": 19.82
    },
    {
      "region": "North West",
      "sla_population": 613,
      "sla_breach_pct": 15.01
    },
    "... (5 more)"
  ],
  "resolution_distribution": [
    {
      "bucket": "< 1 h",
      "sort_order": 1,
      "P1": 29,
      "P2": 43,
      "P3": 66,
      "P4": 13
    },
    {
      "bucket": "1-4 h",
      "sort_order": 2,
      "P1": 63,
      "P2": 184,
      "P3": 389,
      "P4": 260
    },
    {
      "bucket": "4-8 h",
      "sort_order": 3,
      "P1": 86,
      "P2": 205,
      "P3": 259,
      "P4": 181
    },
    "... (4 more)"
  ],
  "first_response": [
    {
      "channel": "Email",
      "tickets": 1372,
      "response_met_pct": 65.6,
      "median_response_minutes": 243.9
    },
    {
      "channel": "Portal",
      "tickets": 2069,
      "response_met_pct": 73.32,
      "median_response_minutes": 199.8
    },
    {
      "channel": "Monitoring Alert",
      "tickets": 736,
      "response_met_pct": 85.73,
      "median_response_minutes": 58.8
    },
    "... (2 more)"
  ],
  "breach_trend": [
    {
      "month": "2025-07",
      "P1": 39.39,
      "P2": 28.57,
      "P3": 21.81,
      "P4": 13.48
    },
    {
      "month": "2025-08",
      "P1": 45.95,
      "P2": 14.29,
      "P3": 21.21,
      "P4": 7.32
    },
    {
      "month": "2025-09",
      "P1": 61.67,
      "P2": 43.5,
      "P3": 26.46,
      "P4": 11.99
    },
    "... (3 more)"
  ]
}
```

## `GET /api/root-causes`

Pareto of incident root causes, root cause x priority matrix, repeat incidents, escalation analysis, slowest subcategories.

Example: `/api/root-causes?start_date=2025-07-01&end_date=2025-12-31`

```json
{
  "filters": {
    "start_date": "2025-07-01",
    "end_date": "2025-12-31",
    "priority": [],
    "team": [],
    "category": [],
    "region": []
  },
  "pareto": [
    {
      "root_cause": "Change-Related",
      "incidents": 980,
      "sla_breach_pct": 30.53,
      "median_resolution_hours": 20.79,
      "pct": 22.38,
      "cumulative_pct": 22.38
    },
    {
      "root_cause": "Configuration Error",
      "incidents": 781,
      "sla_breach_pct": 21.38,
      "median_resolution_hours": 15.73,
      "pct": 17.84,
      "cumulative_pct": 40.21
    },
    {
      "root_cause": "User Error",
      "incidents": 553,
      "sla_breach_pct": 7.45,
      "median_resolution_hours": 8.62,
      "pct": 12.63,
      "cumulative_pct": 52.84
    },
    "... (8 more)"
  ],
  "matrix": [
    {
      "root_cause": "Capacity / Performance",
      "priority": "P1",
      "incidents": 9,
      "sla_breach_pct": 44.4
    },
    {
      "root_cause": "Capacity / Performance",
      "priority": "P2",
      "incidents": 41,
      "sla_breach_pct": 29.3
    },
    {
      "root_cause": "Capacity / Performance",
      "priority": "P3",
      "incidents": 99,
      "sla_breach_pct": 32.7
    },
    "... (41 more)"
  ],
  "repeat_summary": {
    "repeat_incidents": 629,
    "eligible_incidents": 4771,
    "repeat_incident_pct": 13.18
  },
  "repeat_top": [
    {
      "customer_id": "CUST-0455",
      "customer_name": "Granite Renewables plc",
      "subcategory": "ERP Issue",
      "incidents": 23,
      "repeat_incidents": 23,
      "main_root_cause": "Known Error"
    },
    {
      "customer_id": "CUST-0192",
      "customer_name": "Linden Plastics Ltd",
      "subcategory": "SharePoint / OneDrive",
      "incidents": 21,
      "repeat_incidents": 21,
      "main_root_cause": "Known Error"
    },
    {
      "customer_id": "CUST-0407",
      "customer_name": "Riverside Stores Ltd",
      "subcategory": "ERP Issue",
      "incidents": 18,
      "repeat_incidents": 17,
      "main_root_cause": "Known Error"
    },
    "... (7 more)"
  ],
  "escalation": [
    {
      "priority": "P1",
      "escalation_pct": 56.32,
      "median_hours_escalated": 7.01,
      "median_hours_not_escalated": 1.72,
      "breach_pct_escalated": 67.88,
      "breach_pct_not_escalated": 23.36
    },
    {
      "priority": "P2",
      "escalation_pct": 40.92,
      "median_hours_escalated": 13.92,
      "median_hours_not_escalated": 5.25,
      "breach_pct_escalated": 51.06,
      "breach_pct_not_escalated": 16.67
    },
    {
      "priority": "P3",
      "escalation_pct": 21.3,
      "median_hours_escalated": 36.62,
      "median_hours_not_escalated": 15.32,
      "breach_pct_escalated": 44.33,
      "breach_pct_not_escalated": 17.96
    },
    "... (1 more)"
  ],
  "long_categories": [
    {
      "category": "Network",
      "subcategory": "Firewall Rule Change",
      "tickets": 151,
      "median_hours": 41.67,
      "p90_hours": 128.6,
      "sla_breach_pct": 34.44
    },
    {
      "category": "Cloud Services",
      "subcategory": "AWS Resource Issue",
      "tickets": 71,
      "median_hours": 37.99,
      "p90_hours": 120.27,
      "sla_breach_pct": 49.3
    },
    {
      "category": "Network",
      "subcategory": "LAN / Switching",
      "tickets": 127,
      "median_hours": 39.13,
      "p90_hours": 118.63,
      "sla_breach_pct": 56.69
    },
    "... (7 more)"
  ]
}
```

## `GET /api/team-performance`

Team scorecard and monthly workload per team.

Example: `/api/team-performance?start_date=2025-07-01&end_date=2025-12-31`

```json
{
  "filters": {
    "start_date": "2025-07-01",
    "end_date": "2025-12-31",
    "priority": [],
    "team": [],
    "category": [],
    "region": []
  },
  "teams": [
    {
      "team_id": "T01",
      "team_name": "Service Desk",
      "support_tier": "L1",
      "planned_headcount": 18,
      "tickets": 1325,
      "tickets_per_agent_month": 12.27,
      "median_resolution_hours": 8.04,
      "avg_resolution_hours": 15.0,
      "sla_compliance_pct": 93.86,
      "sla_breach_pct": 6.14,
      "avg_csat": 4.25,
      "csat_responses": 496,
      "reopen_pct": 6.02,
      "fcr_pct": 49.72,
      "escalation_pct": 23.02,
      "open_tickets": 60
    },
    {
      "team_id": "T02",
      "team_name": "End User Computing",
      "support_tier": "L2",
      "planned_headcount": 10,
      "tickets": 1039,
      "tickets_per_agent_month": 17.32,
      "median_resolution_hours": 22.95,
      "avg_resolution_hours": 33.61,
      "sla_compliance_pct": 80.84,
      "sla_breach_pct": 19.16,
      "avg_csat": 3.89,
      "csat_responses": 404,
      "reopen_pct": 7.01,
      "fcr_pct": 31.09,
      "escalation_pct": 19.44,
      "open_tickets": 44
    },
    {
      "team_id": "T03",
      "team_name": "Network Operations",
      "support_tier": "L2/L3",
      "planned_headcount": 7,
      "tickets": 904,
      "tickets_per_agent_month": 21.52,
      "median_resolution_hours": 35.06,
      "avg_resolution_hours": 50.18,
      "sla_compliance_pct": 59.72,
      "sla_breach_pct": 40.28,
      "avg_csat": 3.53,
      "csat_responses": 365,
      "reopen_pct": 7.69,
      "fcr_pct": 8.63,
      "escalation_pct": 25.33,
      "open_tickets": 33
    },
    "... (5 more)"
  ],
  "monthly_workload": [
    {
      "month": "2025-07",
      "T01": 212,
      "T02": 173,
      "T03": 145,
      "T04": 153,
      "T05": 142,
      "T06": 79,
      "T07": 68,
      "T08": 49
    },
    {
      "month": "2025-08",
      "T01": 174,
      "T02": 146,
      "T03": 126,
      "T04": 133,
      "T05": 111,
      "T06": 72,
      "T07": 56,
      "T08": 43
    },
    {
      "month": "2025-09",
      "T01": 251,
      "T02": 202,
      "T03": 145,
      "T04": 216,
      "T05": 150,
      "T06": 85,
      "T07": 55,
      "T08": 53
    },
    "... (3 more)"
  ]
}
```

## `GET /api/customer-analysis`

Paginated, searchable, sortable customer table plus highlight lists. Extra params: `page`, `page_size` (1-100), `sort` (tickets, sla_breach_pct, repeat_incidents, repeat_incident_pct, avg_csat, customer_name, escalations, open_tickets), `order` (asc/desc), `search`, `min_tickets`.

Example: `/api/customer-analysis?start_date=2025-07-01&end_date=2025-12-31&sort=sla_breach_pct&min_tickets=10&page_size=3`

```json
{
  "filters": {
    "start_date": "2025-07-01",
    "end_date": "2025-12-31",
    "priority": [],
    "team": [],
    "category": [],
    "region": []
  },
  "summary": {
    "customers": 493,
    "at_risk_customers": 15,
    "tickets": 6226
  },
  "items": [
    {
      "customer_id": "CUST-0184",
      "customer_name": "Dalton Systems Ltd",
      "industry": "Technology",
      "company_size": "Mid-Market",
      "sla_level": "Platinum",
      "hq_region": "South East",
      "customer_success_manager": "Isla Murray",
      "tickets": 10,
      "resolved_tickets": 9,
      "repeat_incidents": 0,
      "repeat_incident_pct": 0.0,
      "breaches": 7,
      "sla_breach_pct": 77.78,
      "avg_csat": 2.5,
      "csat_responses": 4,
      "escalations": 5,
      "open_tickets": 1,
      "is_at_risk": false
    },
    {
      "customer_id": "CUST-0319",
      "customer_name": "Tamar Energy Ltd",
      "industry": "Energy & Utilities",
      "company_size": "Enterprise",
      "sla_level": "Platinum",
      "hq_region": "London",
      "customer_success_manager": "Hannah Lloyd",
      "tickets": 10,
      "resolved_tickets": 10,
      "repeat_incidents": 0,
      "repeat_incident_pct": 0.0,
      "breaches": 7,
      "sla_breach_pct": 70.0,
      "avg_csat": 3.0,
      "csat_responses": 3,
      "escalations": 2,
      "open_tickets": 0,
      "is_at_risk": false
    },
    {
      "customer_id": "CUST-0247",
      "customer_name": "Elmstead Home Group",
      "industry": "Retail",
      "company_size": "SME",
      "sla_level": "Platinum",
      "hq_region": "Wales",
      "customer_success_manager": "Isla Murray",
      "tickets": 16,
      "resolved_tickets": 15,
      "repeat_incidents": 6,
      "repeat_incident_pct": 40.0,
      "breaches": 10,
      "sla_breach_pct": 66.67,
      "avg_csat": 3.27,
      "csat_responses": 11,
      "escalations": 5,
      "open_tickets": 1,
      "is_at_risk": false
    }
  ],
  "total": 235,
  "page": 1,
  "page_size": 3,
  "sort": "sla_breach_pct",
  "order": "desc",
  "highlights": {
    "top_volume": [
      {
        "customer_id": "CUST-0130",
        "customer_name": "Abbey Software Ltd",
        "sla_level": "Gold",
        "tickets": 84,
        "sla_breach_pct": 29.11
      },
      {
        "customer_id": "CUST-0276",
        "customer_name": "Osprey Engineering Group",
        "sla_level": "Gold",
        "tickets": 71,
        "sla_breach_pct": 27.54
      },
      {
        "customer_id": "CUST-0388",
        "customer_name": "Ironbridge Bank plc",
        "sla_level": "Gold",
        "tickets": 69,
        "sla_breach_pct": 21.88
      },
      "... (2 more)"
    ],
    "top_repeat": [
      {
        "customer_id": "CUST-0455",
        "customer_name": "Granite Renewables plc",
        "sla_level": "Platinum",
        "repeat_incidents": 25,
        "repeat_incident_pct": 53.19
      },
      {
        "customer_id": "CUST-0130",
        "customer_name": "Abbey Software Ltd",
        "sla_level": "Gold",
        "repeat_incidents": 24,
        "repeat_incident_pct": 36.92
      },
      {
        "customer_id": "CUST-0192",
        "customer_name": "Linden Plastics Ltd",
        "sla_level": "Gold",
        "repeat_incidents": 24,
        "repeat_incident_pct": 72.73
      },
      "... (2 more)"
    ],
    "low_csat": [
      {
        "customer_id": "CUST-0263",
        "customer_name": "Pembroke Outlets plc",
        "sla_level": "Gold",
        "avg_csat": 2.67,
        "csat_responses": 6
      },
      {
        "customer_id": "CUST-0386",
        "customer_name": "Larkfield Pharma Ltd",
        "sla_level": "Platinum",
        "avg_csat": 2.67,
        "csat_responses": 6
      },
      {
        "customer_id": "CUST-0025",
        "customer_name": "Pennine Industries Group",
        "sla_level": "Gold",
        "avg_csat": 2.71,
        "csat_responses": 7
      },
      "... (2 more)"
    ],
    "high_breach": [
      {
        "customer_id": "CUST-0319",
        "customer_name": "Tamar Energy Ltd",
        "sla_level": "Platinum",
        "sla_breach_pct": 70.0,
        "resolved_tickets": 10
      },
      {
        "customer_id": "CUST-0247",
        "customer_name": "Elmstead Home Group",
        "sla_level": "Platinum",
        "sla_breach_pct": 66.67,
        "resolved_tickets": 15
      },
      {
        "customer_id": "CUST-0025",
        "customer_name": "Pennine Industries Group",
        "sla_level": "Gold",
        "sla_breach_pct": 60.0,
        "resolved_tickets": 10
      },
      "... (2 more)"
    ]
  }
}
```

## `GET /api/tickets`

Paginated ticket list. Extra params: `page`, `page_size`, `sort` (created_at, priority, ticket_id, resolution_time_hours, customer_name, ticket_status), `order`, `search` (ticket id or customer name), `status` (open, resolved, breached, cancelled).

Example: `/api/tickets?status=open&priority=P1&page_size=2`

```json
{
  "filters": {
    "start_date": null,
    "end_date": null,
    "priority": [
      "P1"
    ],
    "team": [],
    "category": [],
    "region": []
  },
  "items": [
    {
      "ticket_id": "TKT-022145",
      "created_at": "2025-12-30T10:17:14",
      "priority": "P1",
      "category": "Infrastructure",
      "subcategory": "Backup Failure",
      "team_id": "T04",
      "team_name": "Infrastructure & Cloud",
      "customer_id": "CUST-0151",
      "customer_name": "Kingsmere Partners Group",
      "channel": "Monitoring Alert",
      "ticket_status": "Pending Customer",
      "sla_target_hours": 4.0,
      "resolution_time_hours": null,
      "sla_breached": null,
      "escalation_flag": true,
      "reopened_count": 0,
      "customer_satisfaction": null,
      "root_cause": null
    },
    {
      "ticket_id": "TKT-022128",
      "created_at": "2025-12-29T20:58:20",
      "priority": "P1",
      "category": "Infrastructure",
      "subcategory": "Server Outage",
      "team_id": "T04",
      "team_name": "Infrastructure & Cloud",
      "customer_id": "CUST-0411",
      "customer_name": "Cotswold Associates LLP",
      "channel": "Phone",
      "ticket_status": "On Hold",
      "sla_target_hours": 12.0,
      "resolution_time_hours": null,
      "sla_breached": null,
      "escalation_flag": false,
      "reopened_count": 0,
      "customer_satisfaction": null,
      "root_cause": null
    }
  ],
  "total": 13,
  "page": 1,
  "page_size": 2,
  "sort": "created_at",
  "order": "desc",
  "status": "open"
}
```

## `GET /api/data-quality`

Data-quality rules applied by the pipeline and the records affected.

Example: `/api/data-quality`

```json
{
  "rules": [
    {
      "rule_id": "M02",
      "issue": "root_cause missing on resolved ticket",
      "action": "kept NULL; excluded where field is required",
      "records": 891
    },
    {
      "rule_id": "M03",
      "issue": "knowledge_base_used missing",
      "action": "kept NULL; excluded where field is required",
      "records": 669
    },
    {
      "rule_id": "BR-RULE-12",
      "issue": "non-standard category label",
      "action": "mapped to controlled category",
      "records": 555
    },
    "... (19 more)"
  ],
  "total_issues": 3253
}
```
