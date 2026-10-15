-- =============================================================================
-- 01_basics_filtering.sql  -  SELECT, filtering, GROUP BY, CASE WHEN
-- All queries read only the analytics layer (they run as the read-only role).
-- Each block starts with "-- @Qnn" and is executed by scripts/run_sql_analysis.py
-- =============================================================================

-- @Q01
-- title: Ticket volume and status mix
-- question: How many valid tickets are in the extract and what state are they in at the snapshot?
-- technique: SELECT, GROUP BY, window SUM() OVER () for percentage of total
-- why: A window total avoids a second query or subquery to compute each status's share.
SELECT ticket_status,
       count(*)                                              AS tickets,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2)    AS pct_of_total
FROM analytics.fact_tickets
GROUP BY ticket_status
ORDER BY tickets DESC;

-- @Q02
-- title: Open P1/P2 tickets already past their SLA target
-- question: Which high-priority tickets need escalation right now because they have already breached?
-- technique: WHERE with multiple predicates, JOIN to dimensions, ORDER BY, LIMIT
-- why: An operational exception list - filtering on the backlog flags defined once in the fact view.
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

-- @Q03
-- title: Channel mix by priority
-- question: Through which channels do tickets of each priority arrive?
-- technique: Conditional aggregation (COUNT ... FILTER / CASE WHEN) to pivot rows into columns
-- why: Produces a compact cross-tab in one pass without a PIVOT operator (which PostgreSQL lacks).
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
