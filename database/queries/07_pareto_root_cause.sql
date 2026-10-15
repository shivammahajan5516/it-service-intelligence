-- =============================================================================
-- 07_pareto_root_cause.sql  -  Pareto analysis, root cause, repeat incidents
-- =============================================================================

-- @Q29
-- title: Root-cause Pareto with ABC classes
-- question: Which few root causes account for most incidents (80/20), and how do they perform?
-- technique: Cumulative SUM() OVER (ORDER BY count DESC) / total, CASE into A/B/C classes
-- why: The cumulative share is the Pareto curve; ABC classes turn it into a priority list.
WITH rc AS (
    SELECT root_cause, count(*) AS incidents,
           round(100 * avg(sla_breached::int), 1) AS breach_pct
    FROM analytics.fact_tickets
    WHERE is_incident AND is_resolved AND root_cause IS NOT NULL
    GROUP BY root_cause
), cum AS (
    SELECT rc.*,
           round(100.0 * incidents / sum(incidents) OVER (), 1) AS pct,
           round(100.0 * sum(incidents) OVER (ORDER BY incidents DESC, root_cause
                                              ROWS UNBOUNDED PRECEDING)
                 / sum(incidents) OVER (), 1)                   AS cumulative_pct
    FROM rc
)
SELECT root_cause, incidents, pct, cumulative_pct, breach_pct,
       CASE WHEN cumulative_pct - pct < 50 THEN 'A (first 50%)'
            WHEN cumulative_pct - pct < 80 THEN 'B (to 80%)'
            ELSE 'C (tail)' END                                 AS pareto_class
FROM cum
ORDER BY incidents DESC, root_cause;

-- @Q30
-- title: Which subcategories generate the SLA breaches?
-- question: Which subcategories account for 80% of all SLA breaches?
-- technique: Pareto on breach COUNT (not rate), cumulative window, filter on the running share
-- why: High-volume subcategories with moderate rates can matter more than rare ones with high rates.
WITH s AS (
    SELECT category, subcategory, count(*) FILTER (WHERE sla_breached) AS breaches,
           round(100 * avg(sla_breached::int), 1) AS breach_rate_pct
    FROM analytics.fact_tickets
    WHERE subcategory IS NOT NULL
    GROUP BY category, subcategory
), c AS (
    SELECT s.*,
           round(100.0 * breaches / sum(breaches) OVER (), 1) AS pct_of_breaches,
           round(100.0 * sum(breaches) OVER (ORDER BY breaches DESC, subcategory ROWS UNBOUNDED PRECEDING)
                 / sum(breaches) OVER (), 1)                  AS cumulative_pct
    FROM s
)
SELECT category, subcategory, breaches, breach_rate_pct, pct_of_breaches, cumulative_pct
FROM c
WHERE cumulative_pct - pct_of_breaches < 80
ORDER BY breaches DESC;

-- @Q31
-- title: Root cause x priority matrix
-- question: How do incidents and breach rates spread across root causes and priorities?
-- technique: Conditional aggregation pivot producing "count (breach %)" cells
-- why: A matrix view lets a Service Delivery Manager spot combinations, e.g. vendor P1s.
SELECT root_cause,
       count(*) FILTER (WHERE priority = 'P1') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P1'))::text, '-') || '%)' AS p1,
       count(*) FILTER (WHERE priority = 'P2') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P2'))::text, '-') || '%)' AS p2,
       count(*) FILTER (WHERE priority = 'P3') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P3'))::text, '-') || '%)' AS p3,
       count(*) FILTER (WHERE priority = 'P4') || ' (' ||
           COALESCE(round(100 * avg(sla_breached::int) FILTER (WHERE priority = 'P4'))::text, '-') || '%)' AS p4,
       count(*)                                                AS total
FROM analytics.fact_tickets
WHERE is_incident AND is_resolved AND root_cause IS NOT NULL
GROUP BY root_cause
ORDER BY total DESC, root_cause;

-- @Q32
-- title: Chronic customer problems (repeat incidents)
-- question: Which customer + subcategory pairs recur most, and what root cause is recorded?
-- technique: GROUP BY two keys, mode() WITHIN GROUP for the most common root cause, HAVING
-- why: mode() names the dominant root cause per pair - the input a Problem Manager needs.
SELECT c.customer_name, f.subcategory,
       count(*)                                                 AS incidents,
       count(*) FILTER (WHERE f.is_repeat_incident)             AS repeat_incidents,
       mode() WITHIN GROUP (ORDER BY f.root_cause)              AS most_common_root_cause,
       round(100 * avg(f.sla_breached::int), 0)                 AS breach_pct,
       min(f.created_date)                                      AS first_seen,
       max(f.created_date)                                      AS last_seen
FROM analytics.fact_tickets f
JOIN analytics.dim_customer c ON c.customer_id = f.customer_id
WHERE f.is_incident AND NOT c.is_placeholder
GROUP BY c.customer_name, f.subcategory
HAVING count(*) FILTER (WHERE f.is_repeat_incident) >= 10
ORDER BY repeat_incidents DESC, incidents DESC, c.customer_name, f.subcategory
LIMIT 15;
