-- =============================================================================
-- 04_window_functions.sql  -  ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD,
--                             running totals, moving averages, NTILE
-- =============================================================================

-- @Q14
-- title: Top 3 customers by volume within each industry
-- question: Who are the three highest-volume customers in every industry?
-- technique: ROW_NUMBER() OVER (PARTITION BY industry ORDER BY tickets DESC)
-- why: ROW_NUMBER gives exactly N rows per group even when volumes tie (top-N-per-group pattern).
WITH ranked AS (
    SELECT industry, customer_name, sla_level, tickets, sla_breach_pct,
           row_number() OVER (PARTITION BY industry ORDER BY tickets DESC, customer_name) AS rn
    FROM analytics.customer_summary
    WHERE industry <> 'Unknown'
)
SELECT industry, rn AS rank_in_industry, customer_name, sla_level, tickets, sla_breach_pct
FROM ranked
WHERE rn <= 3
ORDER BY industry, rn;

-- @Q15
-- title: Team breach-rate ranking, 2024 vs 2025
-- question: How did each team's breach-rate rank change between 2024 and 2025?
-- technique: RANK() and DENSE_RANK() partitioned by year, then a self-join to compare years
-- why: RANK leaves gaps after ties, DENSE_RANK does not; both are shown to illustrate the difference.
WITH yearly AS (
    SELECT team_id, extract(year FROM created_at)::int AS yr,
           round(100 * avg(sla_breached::int), 1) AS breach_pct
    FROM analytics.fact_tickets
    GROUP BY team_id, extract(year FROM created_at)
), ranked AS (
    SELECT y.*,
           rank()       OVER (PARTITION BY yr ORDER BY breach_pct DESC) AS breach_rank,
           dense_rank() OVER (PARTITION BY yr ORDER BY round(breach_pct / 5) * 5 DESC) AS band_dense_rank
    FROM yearly y
)
SELECT t.team_name,
       a.breach_pct AS breach_pct_2024, a.breach_rank AS rank_2024,
       b.breach_pct AS breach_pct_2025, b.breach_rank AS rank_2025,
       b.band_dense_rank AS dense_rank_5pt_band_2025,
       round(b.breach_pct - a.breach_pct, 1) AS change_pp
FROM ranked a
JOIN ranked b ON b.team_id = a.team_id AND b.yr = 2025
JOIN analytics.dim_team t ON t.team_id = a.team_id
WHERE a.yr = 2024
ORDER BY rank_2025;

-- @Q16
-- title: Month-over-month change in SLA breach rate
-- question: How did the breach rate move month to month, and which months saw the biggest jumps?
-- technique: LAG() over months for previous-period comparison
-- why: LAG reads the previous row in order, so MoM change needs no self-join.
SELECT to_char(created_month, 'YYYY-MM')                    AS month,
       tickets,
       sla_breach_pct,
       lag(sla_breach_pct) OVER (ORDER BY created_month)    AS prev_month_pct,
       round(sla_breach_pct - lag(sla_breach_pct) OVER (ORDER BY created_month), 2) AS mom_change_pp,
       round(100.0 * (tickets - lag(tickets) OVER (ORDER BY created_month))
             / lag(tickets) OVER (ORDER BY created_month), 1) AS volume_mom_pct
FROM analytics.kpi_monthly
ORDER BY created_month;

-- @Q17
-- title: How soon does the same problem come back?
-- question: After an incident, how many days until the same customer raises the same subcategory again?
-- technique: LEAD() over customer + subcategory, then percentile_cont on the gap, by category
-- why: LEAD looks forward to the next event in the partition - the natural way to measure recurrence time.
WITH gaps AS (
    SELECT category,
           extract(epoch FROM lead(created_at) OVER (PARTITION BY customer_id, subcategory_id
                                                   ORDER BY created_at) - created_at) / 86400.0 AS days_to_next
    FROM analytics.fact_tickets
    WHERE is_incident AND NOT customer_is_placeholder AND subcategory_id IS NOT NULL
)
SELECT category,
       count(days_to_next)                                                   AS recurrences,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY days_to_next))::numeric, 1) AS median_days_to_next,
       round(100.0 * count(*) FILTER (WHERE days_to_next <= 7) / NULLIF(count(days_to_next), 0), 1)
                                                                             AS pct_within_7_days,
       round(100.0 * count(*) FILTER (WHERE days_to_next <= 30) / NULLIF(count(days_to_next), 0), 1)
                                                                             AS pct_within_30_days
FROM gaps
GROUP BY category
ORDER BY pct_within_30_days DESC;

-- @Q18
-- title: Running total of tickets and breaches by year
-- question: How do cumulative ticket and breach counts build through each year?
-- technique: SUM() OVER (PARTITION BY year ORDER BY month) running totals
-- why: A running total resets each year via PARTITION BY - year-to-date reporting.
SELECT extract(year FROM created_month)::int                   AS year,
       to_char(created_month, 'Mon')                           AS month,
       tickets,
       sum(tickets) OVER w                                     AS ytd_tickets,
       breaches,
       sum(breaches) OVER w                                    AS ytd_breaches,
       round(100.0 * sum(breaches) OVER w / sum(resolved_in_scope) OVER w, 2) AS ytd_breach_pct
FROM (
    SELECT created_month, count(*) AS tickets,
           count(*) FILTER (WHERE sla_breached)      AS breaches,
           count(*) FILTER (WHERE in_sla_population) AS resolved_in_scope
    FROM analytics.fact_tickets
    GROUP BY created_month
) m
WINDOW w AS (PARTITION BY extract(year FROM created_month) ORDER BY created_month)
ORDER BY created_month;

-- @Q19
-- title: Three-month moving averages
-- question: What is the underlying trend in breach rate and median resolution once month-to-month noise is smoothed?
-- technique: AVG() OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
-- why: A ROWS frame gives a trailing 3-month moving average; the first two months are marked partial.
SELECT to_char(created_month, 'YYYY-MM')                                     AS month,
       sla_breach_pct,
       round(avg(sla_breach_pct) OVER w, 2)                                  AS breach_pct_3m_avg,
       median_resolution_hours,
       round(avg(median_resolution_hours) OVER w, 2)                         AS median_res_3m_avg,
       avg_csat,
       round(avg(avg_csat) OVER w, 3)                                        AS csat_3m_avg,
       CASE WHEN count(*) OVER w < 3 THEN 'partial window' END               AS note
FROM analytics.kpi_monthly
WINDOW w AS (ORDER BY created_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
ORDER BY created_month;

-- @Q20
-- title: Customer volume quartiles
-- question: How do outcomes differ between low- and high-volume customers?
-- technique: NTILE(4) to bucket customers into volume quartiles, then aggregate per bucket
-- why: NTILE creates equal-sized segments without hard-coding thresholds.
WITH q AS (
    SELECT cs.*, ntile(4) OVER (ORDER BY tickets) AS volume_quartile
    FROM analytics.customer_summary cs
)
SELECT volume_quartile,
       count(*)                                    AS customers,
       min(tickets)                                AS min_tickets,
       max(tickets)                                AS max_tickets,
       sum(tickets)                                AS total_tickets,
       round(100.0 * sum(tickets) / sum(sum(tickets)) OVER (), 1) AS pct_of_all_tickets,
       round(100.0 * sum(repeat_incidents) / NULLIF(sum(incidents), 0), 1) AS repeat_incident_pct,
       round(avg(sla_breach_pct), 1)               AS avg_customer_breach_pct
FROM q
GROUP BY volume_quartile
ORDER BY volume_quartile;
