"""Endpoint logic: parameterised SQL against the analytics schema + response shaping.

Every function takes a `run` callable:
    run({"name": (sql, params), ...}) -> {"name": [row_dict, ...], ...}
In production `run` is app.db.run (psycopg connection pool). In tests it can be
any executor, which keeps this module free of web-framework and driver imports.
All KPI definitions come from analytics.fact_tickets (docs/05_business_rules.md).
"""
from __future__ import annotations

from typing import Callable

from .filters import Filters, Page, like_pattern, where_clause

Runner = Callable[[dict], dict]

KPI_COLUMNS = """
    count(*)                                                             AS total_tickets,
    count(*) FILTER (WHERE f.is_open)                                    AS open_tickets,
    count(*) FILTER (WHERE f.is_resolved)                                AS resolved_tickets,
    count(*) FILTER (WHERE f.in_sla_population)                          AS sla_population,
    round(100 - 100 * avg(f.sla_breached::int), 2)                       AS sla_compliance_pct,
    round(100 * avg(f.sla_breached::int), 2)                             AS sla_breach_pct,
    round(avg(f.resolution_time_hours) FILTER (WHERE f.in_duration_population), 2) AS avg_resolution_hours,
    round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
           FILTER (WHERE f.in_duration_population))::numeric, 2)        AS median_resolution_hours,
    round(100 * avg(f.fcr_achieved::int), 2)                             AS fcr_pct,
    round(100 * avg(f.is_reopened::int) FILTER (WHERE f.is_resolved), 2) AS reopen_pct,
    round(100 * avg(f.escalation_flag::int), 2)                          AS escalation_pct,
    round(avg(f.customer_satisfaction), 2)                               AS avg_csat,
    count(f.customer_satisfaction)                                       AS csat_responses,
    round(100 * avg(f.is_repeat_incident::int), 2)                       AS repeat_incident_pct
"""

MONTHLY_SQL = """
SELECT to_char(f.created_month, 'YYYY-MM')                               AS month,
       count(*)                                                          AS tickets,
       count(*) FILTER (WHERE f.is_resolved)                             AS resolved,
       round(100 * avg(f.sla_breached::int), 2)                          AS sla_breach_pct,
       round(100 - 100 * avg(f.sla_breached::int), 2)                    AS sla_compliance_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population))::numeric, 2)     AS median_resolution_hours,
       round(100 * avg(f.fcr_achieved::int), 2)                          AS fcr_pct,
       round(100 * avg(f.is_reopened::int) FILTER (WHERE f.is_resolved), 2) AS reopen_pct,
       round(100 * avg(f.escalation_flag::int), 2)                       AS escalation_pct,
       round(avg(f.customer_satisfaction), 2)                            AS avg_csat,
       count(f.customer_satisfaction)                                    AS csat_responses
FROM analytics.fact_tickets f
WHERE {where}
GROUP BY f.created_month
ORDER BY f.created_month
"""


def _kpi_sql(where: str) -> str:
    return f"SELECT {KPI_COLUMNS} FROM analytics.fact_tickets f WHERE {where}"


def _first(rows: list[dict]) -> dict:
    return rows[0] if rows else {}


# --------------------------------------------------------------------------- meta / health
def meta(run: Runner) -> dict:
    r = run({
        "teams": ("SELECT team_id, team_name, support_tier, planned_headcount FROM analytics.dim_team "
                  "ORDER BY team_id", {}),
        "categories": ("SELECT DISTINCT category FROM analytics.dim_category ORDER BY category", {}),
        "regions": ("SELECT DISTINCT region FROM analytics.fact_tickets WHERE region <> 'Unknown' "
                    "ORDER BY region", {}),
        "range": ("SELECT min(created_date)::text AS min_date, max(created_date)::text AS max_date, "
                  "(SELECT snapshot_at::text FROM analytics.extract) AS snapshot_at "
                  "FROM analytics.fact_tickets", {}),
    })
    rng = _first(r["range"])
    return {"teams": r["teams"], "priorities": ["P1", "P2", "P3", "P4"],
            "categories": [x["category"] for x in r["categories"]],
            "regions": [x["region"] for x in r["regions"]],
            "min_date": rng.get("min_date"), "max_date": rng.get("max_date"),
            "snapshot_at": rng.get("snapshot_at"), "synthetic_data": True}


def health(run: Runner) -> dict:
    r = run({"ping": ("SELECT 1 AS ok, (SELECT count(*) FROM analytics.fact_tickets) AS tickets", {})})
    row = _first(r["ping"])
    return {"status": "ok", "database": "ok" if row.get("ok") == 1 else "error",
            "tickets": row.get("tickets")}


# --------------------------------------------------------------------------- overview
def overview(run: Runner, f: Filters) -> dict:
    w, p = where_clause(f)
    queries = {"current": (_kpi_sql(w), p), "monthly": (MONTHLY_SQL.format(where=w), p)}
    prev = f.previous_period()
    if prev:
        pw, pp = where_clause(prev, prefix="prev_")
        queries["previous"] = (_kpi_sql(pw), pp)
    r = run(queries)
    current = _first(r["current"])
    previous = _first(r.get("previous", [])) if prev else None
    if previous is not None and not previous.get("total_tickets"):
        previous = None
    change = {}
    if previous:
        for k, v in current.items():
            pv = previous.get(k)
            if isinstance(v, (int, float)) and isinstance(pv, (int, float)) and not isinstance(v, bool):
                change[k] = round(v - pv, 2)
    return {"filters": f.as_dict(), "current": current, "previous": previous, "change": change,
            "previous_period": ({"start_date": prev.start.isoformat(), "end_date": prev.end.isoformat()}
                                if prev else None),
            "monthly": r["monthly"]}


def trends(run: Runner, f: Filters) -> dict:
    w, p = where_clause(f)
    r = run({"monthly": (MONTHLY_SQL.format(where=w), p)})
    return {"filters": f.as_dict(), "monthly": r["monthly"]}


# --------------------------------------------------------------------------- SLA
def sla_performance(run: Runner, f: Filters) -> dict:
    w, p = where_clause(f)
    q = {
        "by_priority": (f"""
            SELECT f.priority,
                   count(*)                                              AS tickets,
                   count(*) FILTER (WHERE f.in_sla_population)           AS sla_population,
                   round(100 - 100 * avg(f.sla_breached::int), 2)        AS sla_compliance_pct,
                   round(100 * avg(f.sla_breached::int), 2)              AS sla_breach_pct,
                   round(100 * avg(f.response_sla_met::int), 2)          AS response_met_pct,
                   round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
                          FILTER (WHERE f.in_duration_population))::numeric, 2) AS median_resolution_hours,
                   round((percentile_cont(0.9) WITHIN GROUP (ORDER BY f.resolution_time_hours)
                          FILTER (WHERE f.in_duration_population))::numeric, 2) AS p90_resolution_hours
            FROM analytics.fact_tickets f WHERE {w}
            GROUP BY f.priority ORDER BY f.priority""", p),
        "by_category": (f"""
            SELECT f.category,
                   count(*) FILTER (WHERE f.in_sla_population)           AS sla_population,
                   count(*) FILTER (WHERE f.sla_breached)                AS breaches,
                   round(100 * avg(f.sla_breached::int), 2)              AS sla_breach_pct
            FROM analytics.fact_tickets f WHERE {w}
            GROUP BY f.category ORDER BY breaches DESC, f.category""", p),
        "by_team": (f"""
            SELECT f.team_id, t.team_name,
                   count(*) FILTER (WHERE f.in_sla_population)           AS sla_population,
                   count(*) FILTER (WHERE f.sla_breached)                AS breaches,
                   round(100 - 100 * avg(f.sla_breached::int), 2)        AS sla_compliance_pct,
                   round(100 * avg(f.sla_breached::int), 2)              AS sla_breach_pct
            FROM analytics.fact_tickets f JOIN analytics.dim_team t ON t.team_id = f.team_id
            WHERE {w}
            GROUP BY f.team_id, t.team_name ORDER BY sla_breach_pct DESC NULLS LAST, f.team_id""", p),
        "by_region": (f"""
            SELECT f.region,
                   count(*) FILTER (WHERE f.in_sla_population)           AS sla_population,
                   round(100 * avg(f.sla_breached::int), 2)              AS sla_breach_pct
            FROM analytics.fact_tickets f WHERE {w} AND f.region <> 'Unknown'
            GROUP BY f.region ORDER BY f.region""", p),
        "resolution_distribution": (f"""
            SELECT b.bucket, b.sort_order, f.priority, count(*) AS tickets
            FROM analytics.fact_tickets f
            CROSS JOIN LATERAL (SELECT CASE
                 WHEN f.resolution_time_hours < 1   THEN '< 1 h'
                 WHEN f.resolution_time_hours < 4   THEN '1-4 h'
                 WHEN f.resolution_time_hours < 8   THEN '4-8 h'
                 WHEN f.resolution_time_hours < 24  THEN '8-24 h'
                 WHEN f.resolution_time_hours < 72  THEN '1-3 days'
                 WHEN f.resolution_time_hours < 168 THEN '3-7 days'
                 ELSE '> 7 days' END AS bucket,
                 CASE
                 WHEN f.resolution_time_hours < 1   THEN 1 WHEN f.resolution_time_hours < 4 THEN 2
                 WHEN f.resolution_time_hours < 8   THEN 3 WHEN f.resolution_time_hours < 24 THEN 4
                 WHEN f.resolution_time_hours < 72  THEN 5 WHEN f.resolution_time_hours < 168 THEN 6
                 ELSE 7 END AS sort_order) b
            WHERE {w} AND f.in_duration_population
            GROUP BY b.bucket, b.sort_order, f.priority ORDER BY b.sort_order, f.priority""", p),
        "first_response": (f"""
            SELECT f.channel,
                   count(*) FILTER (WHERE f.in_response_population)      AS tickets,
                   round(100 * avg(f.response_sla_met::int), 2)          AS response_met_pct,
                   round((60 * percentile_cont(0.5) WITHIN GROUP (ORDER BY f.first_response_time_hours)
                          FILTER (WHERE f.in_response_population))::numeric, 1) AS median_response_minutes
            FROM analytics.fact_tickets f WHERE {w} AND f.channel IS NOT NULL
            GROUP BY f.channel ORDER BY response_met_pct""", p),
        "breach_trend": (f"""
            SELECT to_char(f.created_month, 'YYYY-MM') AS month, f.priority,
                   round(100 * avg(f.sla_breached::int), 2) AS sla_breach_pct,
                   count(*) FILTER (WHERE f.in_sla_population) AS sla_population
            FROM analytics.fact_tickets f WHERE {w}
            GROUP BY f.created_month, f.priority ORDER BY f.created_month, f.priority""", p),
    }
    r = run(q)
    # pivot the distribution to one row per bucket: {bucket, P1, P2, P3, P4}
    buckets: dict[str, dict] = {}
    for row in r["resolution_distribution"]:
        b = buckets.setdefault(row["bucket"], {"bucket": row["bucket"], "sort_order": row["sort_order"],
                                                "P1": 0, "P2": 0, "P3": 0, "P4": 0})
        b[row["priority"]] = row["tickets"]
    trend: dict[str, dict] = {}
    for row in r["breach_trend"]:
        trend.setdefault(row["month"], {"month": row["month"]})[row["priority"]] = row["sla_breach_pct"]
    return {"filters": f.as_dict(), "by_priority": r["by_priority"], "by_category": r["by_category"],
            "by_team": r["by_team"], "by_region": r["by_region"],
            "resolution_distribution": sorted(buckets.values(), key=lambda x: x["sort_order"]),
            "first_response": r["first_response"], "breach_trend": list(trend.values())}


# --------------------------------------------------------------------------- root causes
def root_causes(run: Runner, f: Filters) -> dict:
    w, p = where_clause(f)
    inc = f"{w} AND f.is_incident AND f.is_resolved AND f.root_cause IS NOT NULL"
    q = {
        "pareto": (f"""
            WITH rc AS (
                SELECT f.root_cause, count(*) AS incidents,
                       round(100 * avg(f.sla_breached::int), 2) AS sla_breach_pct,
                       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
                              FILTER (WHERE f.in_duration_population))::numeric, 2) AS median_resolution_hours
                FROM analytics.fact_tickets f WHERE {inc} GROUP BY f.root_cause)
            SELECT rc.*,
                   round(100.0 * incidents / sum(incidents) OVER (), 2) AS pct,
                   round(100.0 * sum(incidents) OVER (ORDER BY incidents DESC, root_cause ROWS UNBOUNDED PRECEDING)
                         / sum(incidents) OVER (), 2)                  AS cumulative_pct
            FROM rc ORDER BY incidents DESC, root_cause""", p),
        "matrix": (f"""
            SELECT f.root_cause, f.priority, count(*) AS incidents,
                   round(100 * avg(f.sla_breached::int), 1) AS sla_breach_pct
            FROM analytics.fact_tickets f WHERE {inc}
            GROUP BY f.root_cause, f.priority ORDER BY f.root_cause, f.priority""", p),
        "repeat_summary": (f"""
            SELECT count(*) FILTER (WHERE f.is_repeat_incident) AS repeat_incidents,
                   count(*) FILTER (WHERE f.is_repeat_incident IS NOT NULL) AS eligible_incidents,
                   round(100 * avg(f.is_repeat_incident::int), 2) AS repeat_incident_pct
            FROM analytics.fact_tickets f WHERE {w}""", p),
        "repeat_top": (f"""
            SELECT f.customer_id, c.customer_name, f.subcategory,
                   count(*) AS incidents, count(*) FILTER (WHERE f.is_repeat_incident) AS repeat_incidents,
                   mode() WITHIN GROUP (ORDER BY f.root_cause) AS main_root_cause
            FROM analytics.fact_tickets f JOIN analytics.dim_customer c ON c.customer_id = f.customer_id
            WHERE {w} AND f.is_incident AND NOT c.is_placeholder AND f.subcategory IS NOT NULL
            GROUP BY f.customer_id, c.customer_name, f.subcategory
            HAVING count(*) FILTER (WHERE f.is_repeat_incident) > 0
            ORDER BY repeat_incidents DESC, incidents DESC, c.customer_name, f.subcategory LIMIT 10""", p),
        "escalation": (f"""
            SELECT f.priority,
                   round(100 * avg(f.escalation_flag::int), 2) AS escalation_pct,
                   round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
                          FILTER (WHERE f.in_duration_population AND f.escalation_flag))::numeric, 2) AS median_hours_escalated,
                   round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
                          FILTER (WHERE f.in_duration_population AND NOT f.escalation_flag))::numeric, 2) AS median_hours_not_escalated,
                   round(100 * avg(f.sla_breached::int) FILTER (WHERE f.escalation_flag), 2) AS breach_pct_escalated,
                   round(100 * avg(f.sla_breached::int) FILTER (WHERE NOT f.escalation_flag), 2) AS breach_pct_not_escalated
            FROM analytics.fact_tickets f WHERE {w}
            GROUP BY f.priority ORDER BY f.priority""", p),
        "long_categories": (f"""
            SELECT f.category, f.subcategory, count(*) AS tickets,
                   round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours))::numeric, 2) AS median_hours,
                   round((percentile_cont(0.9) WITHIN GROUP (ORDER BY f.resolution_time_hours))::numeric, 2) AS p90_hours,
                   round(100 * avg(f.sla_breached::int), 2) AS sla_breach_pct
            FROM analytics.fact_tickets f
            WHERE {w} AND f.in_duration_population AND f.subcategory IS NOT NULL
            GROUP BY f.category, f.subcategory HAVING count(*) >= 20
            ORDER BY p90_hours DESC, f.subcategory LIMIT 10""", p),
    }
    r = run(q)
    return {"filters": f.as_dict(), "pareto": r["pareto"], "matrix": r["matrix"],
            "repeat_summary": _first(r["repeat_summary"]), "repeat_top": r["repeat_top"],
            "escalation": r["escalation"], "long_categories": r["long_categories"]}


# --------------------------------------------------------------------------- teams
def team_performance(run: Runner, f: Filters) -> dict:
    w, p = where_clause(f)
    q = {
        "teams": (f"""
            WITH months AS (
                SELECT GREATEST(count(DISTINCT f.created_month), 1) AS n FROM analytics.fact_tickets f WHERE {w})
            SELECT t.team_id, t.team_name, t.support_tier, t.planned_headcount,
                   count(f.ticket_id)                                         AS tickets,
                   round(count(f.ticket_id)::numeric / t.planned_headcount / (SELECT n FROM months), 2)
                                                                              AS tickets_per_agent_month,
                   round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
                          FILTER (WHERE f.in_duration_population))::numeric, 2) AS median_resolution_hours,
                   round(avg(f.resolution_time_hours) FILTER (WHERE f.in_duration_population), 2) AS avg_resolution_hours,
                   round(100 - 100 * avg(f.sla_breached::int), 2)             AS sla_compliance_pct,
                   round(100 * avg(f.sla_breached::int), 2)                   AS sla_breach_pct,
                   round(avg(f.customer_satisfaction), 2)                     AS avg_csat,
                   count(f.customer_satisfaction)                             AS csat_responses,
                   round(100 * avg(f.is_reopened::int) FILTER (WHERE f.is_resolved), 2) AS reopen_pct,
                   round(100 * avg(f.fcr_achieved::int), 2)                   AS fcr_pct,
                   round(100 * avg(f.escalation_flag::int), 2)                AS escalation_pct,
                   count(f.ticket_id) FILTER (WHERE f.is_open)                AS open_tickets
            FROM analytics.dim_team t
            LEFT JOIN analytics.fact_tickets f ON f.team_id = t.team_id AND {w}
            GROUP BY t.team_id, t.team_name, t.support_tier, t.planned_headcount
            ORDER BY t.team_id""", p),
        "monthly_workload": (f"""
            SELECT to_char(f.created_month, 'YYYY-MM') AS month, f.team_id, count(*) AS tickets
            FROM analytics.fact_tickets f WHERE {w}
            GROUP BY f.created_month, f.team_id ORDER BY f.created_month, f.team_id""", p),
    }
    r = run(q)
    pivot: dict[str, dict] = {}
    for row in r["monthly_workload"]:
        pivot.setdefault(row["month"], {"month": row["month"]})[row["team_id"]] = row["tickets"]
    teams = [t for t in r["teams"] if f.teams == () or t["team_id"] in f.teams]
    return {"filters": f.as_dict(), "teams": teams, "monthly_workload": list(pivot.values())}


# --------------------------------------------------------------------------- customers
CUSTOMER_SORTS = {
    "tickets": "tickets", "sla_breach_pct": "sla_breach_pct", "repeat_incidents": "repeat_incidents",
    "repeat_incident_pct": "repeat_incident_pct", "avg_csat": "avg_csat", "customer_name": "customer_name",
    "escalations": "escalations", "open_tickets": "open_tickets",
}

CUSTOMER_CTE = """
WITH c AS (
    SELECT d.customer_id, d.customer_name, d.industry, d.company_size, d.sla_level, d.region AS hq_region,
           d.customer_success_manager,
           count(*)                                                AS tickets,
           count(*) FILTER (WHERE f.is_resolved)                   AS resolved_tickets,
           count(*) FILTER (WHERE f.is_repeat_incident)            AS repeat_incidents,
           round(100 * avg(f.is_repeat_incident::int), 2)          AS repeat_incident_pct,
           count(*) FILTER (WHERE f.sla_breached)                  AS breaches,
           round(100 * avg(f.sla_breached::int), 2)                AS sla_breach_pct,
           round(avg(f.customer_satisfaction), 2)                  AS avg_csat,
           count(f.customer_satisfaction)                          AS csat_responses,
           count(*) FILTER (WHERE f.escalation_flag)               AS escalations,
           count(*) FILTER (WHERE f.is_open)                       AS open_tickets,
           COALESCE(bool_or(r.is_at_risk), FALSE)                  AS is_at_risk
    FROM analytics.fact_tickets f
    JOIN analytics.dim_customer d ON d.customer_id = f.customer_id
    LEFT JOIN analytics.customer_risk r ON r.customer_id = f.customer_id
    WHERE {where} AND NOT d.is_placeholder
    GROUP BY d.customer_id, d.customer_name, d.industry, d.company_size, d.sla_level, d.region,
             d.customer_success_manager)
"""


def customer_analysis(run: Runner, f: Filters, pg: Page, min_tickets: int = 1) -> dict:
    w, p = where_clause(f)
    cte = CUSTOMER_CTE.format(where=w)
    params = dict(p, limit=pg.page_size, offset=pg.offset, min_tickets=min_tickets)
    search = ""
    if pg.search:
        search = "AND (c.customer_name ILIKE %(search)s ESCAPE '\\' OR c.customer_id ILIKE %(search)s ESCAPE '\\')"
        params["search"] = like_pattern(pg.search)
    order = f"{CUSTOMER_SORTS[pg.sort]} {'ASC' if pg.order == 'asc' else 'DESC'} NULLS LAST, c.customer_id"
    q = {
        "items": (f"""{cte}
            SELECT c.*, count(*) OVER () AS total_count FROM c
            WHERE c.tickets >= %(min_tickets)s {search}
            ORDER BY {order} LIMIT %(limit)s OFFSET %(offset)s""", params),
        "summary": (f"""{cte}
            SELECT count(*) AS customers, count(*) FILTER (WHERE is_at_risk) AS at_risk_customers,
                   sum(tickets) AS tickets FROM c""", p),
        "top_volume": (f"{cte} SELECT customer_id, customer_name, sla_level, tickets, sla_breach_pct FROM c "
                       "ORDER BY tickets DESC, customer_id LIMIT 5", p),
        "top_repeat": (f"{cte} SELECT customer_id, customer_name, sla_level, repeat_incidents, repeat_incident_pct "
                       "FROM c WHERE repeat_incidents > 0 ORDER BY repeat_incidents DESC, customer_id LIMIT 5", p),
        "low_csat": (f"{cte} SELECT customer_id, customer_name, sla_level, avg_csat, csat_responses FROM c "
                     "WHERE csat_responses >= 5 ORDER BY avg_csat ASC, customer_id LIMIT 5", p),
        "high_breach": (f"{cte} SELECT customer_id, customer_name, sla_level, sla_breach_pct, resolved_tickets FROM c "
                        "WHERE resolved_tickets >= 10 ORDER BY sla_breach_pct DESC NULLS LAST, customer_id LIMIT 5", p),
    }
    r = run(q)
    items = r["items"]
    total = items[0]["total_count"] if items else 0
    for it in items:
        it.pop("total_count", None)
    return {"filters": f.as_dict(), "summary": _first(r["summary"]), "items": items, "total": total,
            "page": pg.page, "page_size": pg.page_size, "sort": pg.sort, "order": pg.order,
            "highlights": {"top_volume": r["top_volume"], "top_repeat": r["top_repeat"],
                           "low_csat": r["low_csat"], "high_breach": r["high_breach"]}}


# --------------------------------------------------------------------------- tickets
TICKET_SORTS = {"created_at": "f.created_at", "priority": "f.priority", "ticket_id": "f.ticket_id",
                "resolution_time_hours": "f.resolution_time_hours", "customer_name": "c.customer_name",
                "ticket_status": "f.ticket_status"}
TICKET_STATUS = {"open": "f.is_open", "resolved": "f.is_resolved", "breached": "f.sla_breached",
                 "cancelled": "f.is_cancelled"}


def tickets(run: Runner, f: Filters, pg: Page, status: str | None = None) -> dict:
    w, p = where_clause(f)
    params = dict(p, limit=pg.page_size, offset=pg.offset)
    extra = ""
    if status:
        extra += f" AND {TICKET_STATUS[status]}"
    if pg.search:
        extra += " AND (f.ticket_id ILIKE %(search)s ESCAPE '\\' OR c.customer_name ILIKE %(search)s ESCAPE '\\')"
        params["search"] = like_pattern(pg.search)
    order = f"{TICKET_SORTS[pg.sort]} {'ASC' if pg.order == 'asc' else 'DESC'} NULLS LAST, f.ticket_id"
    sql = f"""
        SELECT f.ticket_id, to_char(f.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at,
               f.priority, f.category, f.subcategory, f.team_id, t.team_name, f.customer_id, c.customer_name,
               f.channel, f.ticket_status, f.sla_target_hours, f.resolution_time_hours, f.sla_breached,
               f.escalation_flag, f.reopened_count, f.customer_satisfaction, f.root_cause,
               count(*) OVER () AS total_count
        FROM analytics.fact_tickets f
        JOIN analytics.dim_team t     ON t.team_id = f.team_id
        JOIN analytics.dim_customer c ON c.customer_id = f.customer_id
        WHERE {w}{extra}
        ORDER BY {order}
        LIMIT %(limit)s OFFSET %(offset)s"""
    r = run({"items": (sql, params)})
    items = r["items"]
    total = items[0]["total_count"] if items else 0
    for it in items:
        it.pop("total_count", None)
    return {"filters": f.as_dict(), "items": items, "total": total, "page": pg.page,
            "page_size": pg.page_size, "sort": pg.sort, "order": pg.order, "status": status}


def data_quality(run: Runner) -> dict:
    r = run({"rules": ("SELECT rule_id, issue, action, records FROM analytics.dq_summary "
                       "ORDER BY records DESC, rule_id", {})})
    return {"rules": r["rules"], "total_issues": sum(x["records"] for x in r["rules"])}
