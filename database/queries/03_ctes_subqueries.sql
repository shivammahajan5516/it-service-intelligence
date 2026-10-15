-- =============================================================================
-- 03_ctes_subqueries.sql  -  CTEs, multiple CTEs, correlated subqueries, EXISTS
-- =============================================================================

-- @Q09
-- title: Teams slower than the company median
-- question: Which teams' median resolution time exceeds the company-wide median, and by how much?
-- technique: CTE for the benchmark, CROSS JOIN to compare every team against it
-- why: The CTE names the benchmark once; the main query reads like the business question.
WITH company AS (
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours) AS median_h
    FROM analytics.fact_tickets WHERE in_duration_population
), team AS (
    SELECT team_id,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours) AS median_h,
           count(*) AS n
    FROM analytics.fact_tickets WHERE in_duration_population
    GROUP BY team_id
)
SELECT d.team_name, t.n AS resolved_tickets,
       round(t.median_h::numeric, 1)                      AS team_median_hours,
       round(c.median_h::numeric, 1)                      AS company_median_hours,
       round((t.median_h / c.median_h)::numeric, 2)       AS ratio_to_company
FROM team t
CROSS JOIN company c
JOIN analytics.dim_team d USING (team_id)
WHERE t.median_h > c.median_h
ORDER BY ratio_to_company DESC;

-- @Q10
-- title: Does workload drive breaches? (team-quarter)
-- question: Across team-quarters, is a higher ticket load per agent associated with a higher breach rate?
-- technique: Multiple chained CTEs, date_trunc, then corr() and regr_slope() statistical aggregates
-- why: Builds the analysis grain step by step; corr() gives a single association measure in SQL.
WITH team_quarter AS (
    SELECT team_id, date_trunc('quarter', created_at)::date AS quarter,
           count(*)                       AS tickets,
           avg(sla_breached::int)         AS breach_rate
    FROM analytics.fact_tickets
    GROUP BY team_id, date_trunc('quarter', created_at)
), loaded AS (
    SELECT q.*, q.tickets / 3.0 / t.planned_headcount AS tickets_per_agent_month
    FROM team_quarter q
    JOIN analytics.dim_team t USING (team_id)
), summary AS (
    SELECT count(*)                                                  AS team_quarters,
           round(corr(tickets_per_agent_month, breach_rate)::numeric, 3) AS pearson_r,
           round((100 * regr_slope(breach_rate, tickets_per_agent_month))::numeric, 2)
                                                                     AS breach_pp_per_extra_ticket
    FROM loaded
)
SELECT 'All team-quarters' AS scope, * FROM summary
UNION ALL
SELECT 'Excluding Service Desk (T01)', count(*),
       round(corr(tickets_per_agent_month, breach_rate)::numeric, 3),
       round((100 * regr_slope(breach_rate, tickets_per_agent_month))::numeric, 2)
FROM loaded WHERE team_id <> 'T01';

-- @Q11
-- title: Customers less satisfied than their industry peers
-- question: Which customers (>= 10 survey responses) have average CSAT at least 0.5 below their industry average?
-- technique: Correlated subquery referencing the outer row's industry
-- why: The benchmark differs per row (per industry), which is what a correlated subquery expresses.
SELECT cs.customer_name, cs.industry, cs.csat_responses, cs.avg_csat,
       round((SELECT avg(f.customer_satisfaction)
              FROM analytics.fact_tickets f
              JOIN analytics.dim_customer c2 ON c2.customer_id = f.customer_id
              WHERE c2.industry = cs.industry), 2)          AS industry_avg_csat
FROM analytics.customer_summary cs
WHERE cs.csat_responses >= 10
  AND cs.avg_csat <= (SELECT avg(f.customer_satisfaction)
                      FROM analytics.fact_tickets f
                      JOIN analytics.dim_customer c2 ON c2.customer_id = f.customer_id
                      WHERE c2.industry = cs.industry) - 0.5
ORDER BY cs.avg_csat, cs.csat_responses DESC, cs.customer_name
LIMIT 15;

-- @Q12
-- title: Customers with both a P1 breach and repeat incidents (last 90 days)
-- question: Which customers had a breached P1 AND at least three repeat incidents in the final 90 days?
-- technique: EXISTS and a correlated count subquery, relative date window from the extract snapshot
-- why: EXISTS stops at the first match and states "at least one" intent clearly.
SELECT c.customer_id, c.customer_name, c.sla_level, c.customer_success_manager,
       (SELECT count(*) FROM analytics.fact_tickets r
        WHERE r.customer_id = c.customer_id AND r.is_repeat_incident
          AND r.created_at > (SELECT snapshot_at FROM analytics.extract) - interval '90 days') AS repeat_incidents_90d
FROM analytics.dim_customer c
WHERE EXISTS (SELECT 1 FROM analytics.fact_tickets f
              WHERE f.customer_id = c.customer_id AND f.priority = 'P1' AND f.sla_breached
                AND f.created_at > (SELECT snapshot_at FROM analytics.extract) - interval '90 days')
  AND (SELECT count(*) FROM analytics.fact_tickets r
       WHERE r.customer_id = c.customer_id AND r.is_repeat_incident
         AND r.created_at > (SELECT snapshot_at FROM analytics.extract) - interval '90 days') >= 3
ORDER BY repeat_incidents_90d DESC, c.customer_name;

-- @Q13
-- title: Out-of-hours queueing effect
-- question: For P3/P4 tickets, how much more often do out-of-hours tickets breach, by team operating model?
-- technique: CTE + CASE to label groups, conditional aggregation, ratio of rates
-- why: Separates 24x7 teams from business-hours teams to isolate the queueing mechanism.
WITH labelled AS (
    SELECT t.operating_model,
           CASE WHEN f.is_out_of_hours THEN 'out_of_hours' ELSE 'in_hours' END AS logged,
           f.sla_breached
    FROM analytics.fact_tickets f
    JOIN analytics.dim_team t USING (team_id)
    WHERE f.priority IN ('P3', 'P4')
)
SELECT operating_model,
       count(*) FILTER (WHERE logged = 'in_hours' AND sla_breached IS NOT NULL)     AS n_in_hours,
       round(100 * avg(sla_breached::int) FILTER (WHERE logged = 'in_hours'), 1)     AS breach_pct_in_hours,
       count(*) FILTER (WHERE logged = 'out_of_hours' AND sla_breached IS NOT NULL) AS n_out_of_hours,
       round(100 * avg(sla_breached::int) FILTER (WHERE logged = 'out_of_hours'), 1) AS breach_pct_out_of_hours,
       round(avg(sla_breached::int) FILTER (WHERE logged = 'out_of_hours')
             / NULLIF(avg(sla_breached::int) FILTER (WHERE logged = 'in_hours'), 0), 2) AS relative_risk
FROM labelled
GROUP BY operating_model
ORDER BY relative_risk DESC;
