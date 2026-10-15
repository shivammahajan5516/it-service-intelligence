-- =============================================================================
-- 02_joins_aggregation.sql  -  JOINs, GROUP BY, HAVING, conditional aggregation
-- =============================================================================

-- @Q04
-- title: SLA breach rate by support team
-- question: Which resolver teams breach SLA most often, and on how many tickets?
-- technique: INNER JOIN fact to team dimension, GROUP BY, AVG of a boolean outcome
-- why: sla_breached is NULL outside the SLA population, so AVG() automatically uses the right denominator.
SELECT t.team_id, t.team_name, t.support_tier,
       count(*) FILTER (WHERE f.in_sla_population)            AS resolved_in_scope,
       count(*) FILTER (WHERE f.sla_breached)                 AS breaches,
       round(100 * avg(f.sla_breached::int), 1)               AS sla_breach_pct
FROM analytics.fact_tickets f
JOIN analytics.dim_team t ON t.team_id = f.team_id
GROUP BY t.team_id, t.team_name, t.support_tier
ORDER BY sla_breach_pct DESC, t.team_id;

-- @Q05
-- title: Categories breaching above the company average
-- question: Which incident categories have a breach rate above the overall rate (minimum 200 tickets)?
-- technique: GROUP BY with HAVING, scalar subquery for the benchmark
-- why: HAVING filters on the aggregated rate; the subquery keeps the benchmark in the same statement.
SELECT f.category,
       count(*) FILTER (WHERE f.in_sla_population)            AS resolved_in_scope,
       round(100 * avg(f.sla_breached::int), 1)               AS sla_breach_pct,
       round(100 * (SELECT avg(sla_breached::int) FROM analytics.fact_tickets), 1) AS company_breach_pct
FROM analytics.fact_tickets f
GROUP BY f.category
HAVING count(*) FILTER (WHERE f.in_sla_population) >= 200
   AND avg(f.sla_breached::int) > (SELECT avg(sla_breached::int) FROM analytics.fact_tickets)
ORDER BY sla_breach_pct DESC;

-- @Q06
-- title: Breach rate by contracted SLA level and company size
-- question: Do tighter contracts (Platinum) breach more often than looser ones (Bronze)?
-- technique: JOIN to customer dimension, two-level GROUP BY, ORDER BY a CASE expression
-- why: Tests whether tighter targets, not slower work, drive breaches; CASE gives business sort order.
SELECT c.sla_level, c.company_size,
       count(*) FILTER (WHERE f.in_sla_population)            AS resolved_in_scope,
       round(100 * avg(f.sla_breached::int), 1)               AS sla_breach_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population))::numeric, 1) AS median_resolution_hours
FROM analytics.fact_tickets f
JOIN analytics.dim_customer c ON c.customer_id = f.customer_id
WHERE NOT c.is_placeholder
GROUP BY c.sla_level, c.company_size
ORDER BY CASE c.sla_level WHEN 'Platinum' THEN 1 WHEN 'Gold' THEN 2 WHEN 'Silver' THEN 3 ELSE 4 END,
         CASE c.company_size WHEN 'Large Enterprise' THEN 1 WHEN 'Enterprise' THEN 2
                             WHEN 'Mid-Market' THEN 3 ELSE 4 END;

-- @Q07
-- title: Agent experience level vs outcomes
-- question: How do resolution time, escalation and reopen rates differ by agent experience?
-- technique: LEFT JOIN to agent dimension (keeps unassigned tickets), conditional aggregation
-- why: A LEFT JOIN makes the unassigned group visible instead of silently dropping it.
SELECT COALESCE(a.experience_level, '(unassigned)')       AS experience_level,
       count(*)                                           AS tickets,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
              FILTER (WHERE f.in_duration_population))::numeric, 1) AS median_resolution_hours,
       round(100 * avg(f.escalation_flag::int), 1)        AS escalation_pct,
       round(100 * avg(f.is_reopened::int) FILTER (WHERE f.is_resolved), 1) AS reopen_pct,
       round(100 * avg(f.sla_breached::int), 1)           AS sla_breach_pct
FROM analytics.fact_tickets f
LEFT JOIN analytics.dim_agent a ON a.agent_id = f.agent_id
GROUP BY COALESCE(a.experience_level, '(unassigned)')
ORDER BY median_resolution_hours DESC NULLS LAST;

-- @Q08
-- title: First-contact resolution by channel
-- question: Which channels give the best first-contact resolution, and how does KB use change it?
-- technique: Conditional aggregation with FILTER on two dimensions (channel x KB used)
-- why: Shows the FCR rate with and without knowledge-base use side by side for each channel.
SELECT channel,
       count(*) FILTER (WHERE in_fcr_population)                         AS fcr_population,
       round(100 * avg(fcr_achieved::int), 1)                            AS fcr_pct,
       round(100 * avg(fcr_achieved::int) FILTER (WHERE knowledge_base_used), 1)     AS fcr_pct_kb_used,
       round(100 * avg(fcr_achieved::int) FILTER (WHERE NOT knowledge_base_used), 1) AS fcr_pct_no_kb
FROM analytics.fact_tickets
WHERE channel IS NOT NULL
GROUP BY channel
ORDER BY fcr_pct DESC;
