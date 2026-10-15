-- =============================================================================
-- 06_sla_percentiles.sql  -  SLA breach analysis and percentile analysis
-- =============================================================================

-- @Q25
-- title: Resolution-time percentiles by priority
-- question: What does the full distribution of resolution time look like per priority, against target?
-- technique: percentile_cont with an array of fractions (P50/P75/P90/P95) in one pass
-- why: Means hide skew; percentiles show how long the slowest 10% of customers wait.
SELECT priority, resolved_tickets, mean_h,
       round(pct[1]::numeric, 1) AS p50_h,
       round(pct[2]::numeric, 1) AS p75_h,
       round(pct[3]::numeric, 1) AS p90_h,
       round(pct[4]::numeric, 1) AS p95_h,
       min_target_h, max_target_h
FROM (
    SELECT priority,
           count(*)                                    AS resolved_tickets,
           round(avg(resolution_time_hours), 1)        AS mean_h,
           percentile_cont(ARRAY[0.5, 0.75, 0.9, 0.95])
               WITHIN GROUP (ORDER BY resolution_time_hours) AS pct,
           min(sla_target_hours)                       AS min_target_h,
           max(sla_target_hours)                       AS max_target_h
    FROM analytics.fact_tickets
    WHERE in_duration_population
    GROUP BY priority
) s
ORDER BY priority;

-- @Q26
-- title: How badly are SLAs missed?
-- question: When a ticket breaches, by how much does it overrun its target?
-- technique: width_bucket() on the overrun ratio, CASE labels, distribution percentages
-- why: Distinguishes near-misses (fixable with small process changes) from severe overruns.
WITH breached AS (
    SELECT priority, resolution_time_hours / sla_target_hours AS ratio
    FROM analytics.fact_tickets
    WHERE sla_breached
)
SELECT CASE width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0])
            WHEN 1 THEN '1.00-1.25x target'
            WHEN 2 THEN '1.25-1.5x'
            WHEN 3 THEN '1.5-2x'
            WHEN 4 THEN '2-3x'
            WHEN 5 THEN '3-5x'
            ELSE '5x or more' END                                   AS overrun_band,
       count(*)                                                     AS breaches,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)           AS pct_of_breaches,
       round(100.0 * sum(count(*)) OVER (ORDER BY width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0]))
             / sum(count(*)) OVER (), 1)                            AS cumulative_pct,
       count(*) FILTER (WHERE priority IN ('P1', 'P2'))             AS of_which_p1_p2
FROM breached
GROUP BY width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0])
ORDER BY width_bucket(ratio, ARRAY[1.0, 1.25, 1.5, 2.0, 3.0, 5.0]);

-- @Q27
-- title: First-response SLA by priority and channel
-- question: Are first-response targets being met, and which channel/priority combinations miss most?
-- technique: GROUP BY GROUPING SETS for channel detail plus per-priority subtotals in one result
-- why: GROUPING SETS returns detail and subtotal rows together; GROUPING() labels the subtotal rows.
SELECT priority,
       CASE WHEN grouping(channel) = 1 THEN '(all channels)' ELSE channel END AS channel,
       count(*) FILTER (WHERE in_response_population)               AS tickets,
       round(100 * avg(response_sla_met::int), 1)                   AS response_met_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY first_response_time_hours)
              FILTER (WHERE in_response_population))::numeric * 60, 0) AS median_response_minutes
FROM analytics.fact_tickets
WHERE channel IS NOT NULL
GROUP BY GROUPING SETS ((priority, channel), (priority))
ORDER BY priority, grouping(channel) DESC, response_met_pct;

-- @Q28
-- title: Escalation impact by priority
-- question: How much longer do escalated tickets take, and how much more often do they breach?
-- technique: Conditional aggregation of medians with FILTER, ratio of escalated vs not
-- why: Compares like-for-like priorities so the priority mix does not distort the escalation effect.
SELECT priority,
       round(100 * avg(escalation_flag::int), 1)                                           AS escalation_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
              FILTER (WHERE in_duration_population AND NOT escalation_flag))::numeric, 1)  AS median_h_not_escalated,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
              FILTER (WHERE in_duration_population AND escalation_flag))::numeric, 1)      AS median_h_escalated,
       round(100 * avg(sla_breached::int) FILTER (WHERE NOT escalation_flag), 1)           AS breach_pct_not_escalated,
       round(100 * avg(sla_breached::int) FILTER (WHERE escalation_flag), 1)               AS breach_pct_escalated
FROM analytics.fact_tickets
GROUP BY priority
ORDER BY priority;
