-- =============================================================================
-- 08_customer_team.sql  -  customer-level aggregation, team comparison,
--                          driver checks and a negative control
-- =============================================================================

-- @Q33
-- title: At-risk customer list (BR-RULE-14)
-- question: Which customers meet the at-risk rule in the last 90 days, and why?
-- technique: Read the rule view, build a human-readable reason with CONCAT_WS and CASE
-- why: CSMs need the evidence behind each flag, not just a yes/no.
SELECT customer_name, sla_level, customer_success_manager, resolved_tickets,
       sla_breach_pct_90d, repeat_incident_pct_90d, avg_csat_90d, csat_responses_90d,
       concat_ws('; ',
           CASE WHEN flag_high_breach THEN 'breach rate >= 1.5x company' END,
           CASE WHEN flag_repeat_incidents THEN 'repeat incidents >= 20%' END,
           CASE WHEN flag_low_csat THEN 'CSAT <= 3.5' END)               AS reasons
FROM analytics.customer_risk
WHERE is_at_risk
ORDER BY risk_flags DESC, sla_breach_pct_90d DESC, customer_name;

-- @Q34
-- title: Team scorecard against the company average
-- question: How does each team compare with the average team on every headline KPI?
-- technique: AVG() OVER () across the result set for deltas; RANK() for a league position
-- why: Window aggregates over the whole result give the benchmark without a second query.
SELECT team_name, tickets, tickets_per_agent_per_month,
       sla_breach_pct,
       round(sla_breach_pct - avg(sla_breach_pct) OVER (), 1)        AS breach_vs_avg_pp,
       median_resolution_hours,
       fcr_pct,
       round(fcr_pct - avg(fcr_pct) OVER (), 1)                      AS fcr_vs_avg_pp,
       reopen_pct, avg_csat,
       rank() OVER (ORDER BY sla_breach_pct)                         AS sla_rank,
       rank() OVER (ORDER BY avg_csat DESC)                          AS csat_rank
FROM analytics.kpi_team
ORDER BY sla_rank;

-- @Q35
-- title: Do workarounds come back?
-- question: How does the reopen rate vary by resolution type, and what does a reopen cost in CSAT?
-- technique: GROUP BY with conditional averages; CSAT split by reopened vs not
-- why: Links a process choice (workaround vs permanent fix) to rework and customer experience.
SELECT resolution_type,
       count(*)                                                         AS resolved,
       round(100 * avg(is_reopened::int), 1)                            AS reopen_pct,
       round(avg(customer_satisfaction) FILTER (WHERE NOT is_reopened), 2) AS csat_not_reopened,
       round(avg(customer_satisfaction) FILTER (WHERE is_reopened), 2)     AS csat_reopened
FROM analytics.fact_tickets
WHERE is_resolved AND resolution_type IS NOT NULL
GROUP BY resolution_type
HAVING count(*) >= 100
ORDER BY reopen_pct DESC, resolution_type;

-- @Q36
-- title: Knowledge-base use by team
-- question: How often does each team use the knowledge base, and is KB use associated with better outcomes?
-- technique: Conditional aggregation by team and KB flag, difference in FCR rates
-- why: Identifies teams where KB adoption is low but the association with FCR is strong.
SELECT t.team_name,
       round(100 * avg(f.knowledge_base_used::int), 1)                                AS kb_usage_pct,
       round(100 * avg(f.fcr_achieved::int) FILTER (WHERE f.knowledge_base_used), 1)     AS fcr_pct_with_kb,
       round(100 * avg(f.fcr_achieved::int) FILTER (WHERE NOT f.knowledge_base_used), 1) AS fcr_pct_without_kb,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population AND f.knowledge_base_used))::numeric, 1)     AS median_h_with_kb,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population AND NOT f.knowledge_base_used))::numeric, 1) AS median_h_without_kb
FROM analytics.fact_tickets f
JOIN analytics.dim_team t USING (team_id)
GROUP BY t.team_name
ORDER BY kb_usage_pct, t.team_name;

-- @Q37
-- title: Negative control - is region a real driver?
-- question: Regions show different breach rates; is that region itself, or just a different mix of teams, priorities and contracts?
-- technique: Indirect standardisation - expected breaches from team x priority x SLA-level rates, two models compared
-- why: Observed/expected near 1.0 after adjustment means the raw regional gap is explained by work and contract mix.
WITH cell_tp AS (
    SELECT team_id, priority, avg(sla_breached::int) AS rate
    FROM analytics.fact_tickets GROUP BY team_id, priority
), cell_tps AS (
    SELECT team_id, priority, sla_level, avg(sla_breached::int) AS rate
    FROM analytics.fact_tickets GROUP BY team_id, priority, sla_level
)
SELECT f.region,
       count(*) FILTER (WHERE f.in_sla_population)                          AS resolved_in_scope,
       round(100 * avg(f.sla_breached::int), 1)                             AS observed_breach_pct,
       round(avg(f.sla_breached::int) / avg(a.rate) FILTER (WHERE f.in_sla_population), 2)
                                                                            AS obs_to_exp_team_priority,
       round(avg(f.sla_breached::int) / avg(b.rate) FILTER (WHERE f.in_sla_population), 2)
                                                                            AS obs_to_exp_plus_sla_level,
       round(100 * avg(f.sla_breached::int) FILTER (WHERE f.sla_level = 'Platinum'), 1) AS platinum_breach_pct,
       round(100.0 * count(*) FILTER (WHERE f.sla_level = 'Platinum' AND f.in_sla_population)
             / count(*) FILTER (WHERE f.in_sla_population), 1)              AS pct_platinum_tickets
FROM analytics.fact_tickets f
JOIN cell_tp  a USING (team_id, priority)
JOIN cell_tps b USING (team_id, priority, sla_level)
WHERE f.region <> 'Unknown'
GROUP BY f.region
ORDER BY observed_breach_pct DESC;
