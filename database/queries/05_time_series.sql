-- =============================================================================
-- 05_time_series.sql  -  date/time functions, YoY, rolling windows, trends
-- =============================================================================

-- @Q21
-- title: When do tickets arrive? (weekday x time band)
-- question: How is ticket volume distributed across the week and the working day?
-- technique: EXTRACT(isodow / hour), CASE time bands, conditional aggregation into a heatmap grid
-- why: Shows staffing demand; EXTRACT and CASE turn timestamps into business time bands.
SELECT to_char(created_at, 'ID-Dy')                                          AS weekday,
       count(*) FILTER (WHERE extract(hour FROM created_at) < 8)              AS "00-08",
       count(*) FILTER (WHERE extract(hour FROM created_at) BETWEEN 8 AND 11) AS "08-12",
       count(*) FILTER (WHERE extract(hour FROM created_at) BETWEEN 12 AND 13) AS "12-14",
       count(*) FILTER (WHERE extract(hour FROM created_at) BETWEEN 14 AND 17) AS "14-18",
       count(*) FILTER (WHERE extract(hour FROM created_at) >= 18)            AS "18-24",
       count(*)                                                              AS total,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                    AS pct_of_week
FROM analytics.fact_tickets
GROUP BY to_char(created_at, 'ID-Dy')
ORDER BY weekday;

-- @Q22
-- title: Year-over-year by quarter
-- question: How did volume, breach rate and CSAT change between each quarter of 2024 and the same quarter of 2025?
-- technique: date_part, conditional aggregation by year, YoY growth calculation
-- why: Comparing like-for-like quarters removes seasonality from the trend.
SELECT 'Q' || extract(quarter FROM created_at)                                 AS quarter,
       count(*) FILTER (WHERE extract(year FROM created_at) = 2024)            AS tickets_2024,
       count(*) FILTER (WHERE extract(year FROM created_at) = 2025)            AS tickets_2025,
       round(100.0 * (count(*) FILTER (WHERE extract(year FROM created_at) = 2025)
                    - count(*) FILTER (WHERE extract(year FROM created_at) = 2024))
             / count(*) FILTER (WHERE extract(year FROM created_at) = 2024), 1) AS volume_yoy_pct,
       round(100 * avg(sla_breached::int) FILTER (WHERE extract(year FROM created_at) = 2024), 1) AS breach_pct_2024,
       round(100 * avg(sla_breached::int) FILTER (WHERE extract(year FROM created_at) = 2025), 1) AS breach_pct_2025,
       round(avg(customer_satisfaction) FILTER (WHERE extract(year FROM created_at) = 2024), 2) AS csat_2024,
       round(avg(customer_satisfaction) FILTER (WHERE extract(year FROM created_at) = 2025), 2) AS csat_2025
FROM analytics.fact_tickets
GROUP BY extract(quarter FROM created_at)
ORDER BY quarter;

-- @Q23
-- title: Detecting volume spikes (major incidents)
-- question: Which days had volume far above their recent normal level?
-- technique: Calendar LEFT JOIN (zero-filled days), RANGE window over a 28-day interval, ratio to baseline
-- why: The date dimension guarantees days with no tickets still count; RANGE uses real dates, not rows.
WITH daily AS (
    SELECT d.date, d.day_name, d.is_working_day, count(f.ticket_id) AS tickets
    FROM analytics.dim_date d
    LEFT JOIN analytics.fact_tickets f ON f.created_date = d.date
    GROUP BY d.date, d.day_name, d.is_working_day
), baseline AS (
    SELECT daily.*,
           avg(tickets) FILTER (WHERE is_working_day) OVER (
               ORDER BY date RANGE BETWEEN interval '28 days' PRECEDING AND interval '1 day' PRECEDING
           ) AS prior_28d_working_day_avg
    FROM daily
)
SELECT date, day_name, tickets,
       round(prior_28d_working_day_avg, 1)                           AS prior_28d_avg,
       round(tickets / NULLIF(prior_28d_working_day_avg, 0), 2)      AS ratio_to_normal,
       (SELECT string_agg(sub || ' (' || n || ')', ', ' ORDER BY n DESC)
        FROM (SELECT f.subcategory AS sub, count(*) AS n FROM analytics.fact_tickets f
              WHERE f.created_date = b.date GROUP BY f.subcategory ORDER BY n DESC LIMIT 2) top) AS top_subcategories
FROM baseline b
WHERE prior_28d_working_day_avg IS NOT NULL
ORDER BY ratio_to_normal DESC
LIMIT 8;

-- @Q24
-- title: Change-related incidents over time
-- question: Is the share of incidents caused by changes growing, and how do they perform against SLA?
-- technique: date_trunc('quarter'), conditional aggregation, window LAG for quarter-over-quarter change
-- why: Tests the hypothesis that weak change control is a growing source of incidents (KPI-15).
WITH q AS (
    SELECT date_trunc('quarter', created_at)::date AS quarter,
           count(*) FILTER (WHERE root_cause IS NOT NULL)                AS incidents_known_cause,
           count(*) FILTER (WHERE root_cause = 'Change-Related')         AS change_related,
           round(100 * avg(sla_breached::int) FILTER (WHERE root_cause = 'Change-Related'), 1) AS change_breach_pct,
           round(100 * avg(sla_breached::int) FILTER (WHERE root_cause <> 'Change-Related'), 1) AS other_breach_pct
    FROM analytics.fact_tickets
    WHERE is_incident AND is_resolved
    GROUP BY date_trunc('quarter', created_at)
)
SELECT to_char(quarter, 'YYYY-"Q"Q')                                  AS quarter,
       incidents_known_cause, change_related,
       round(100.0 * change_related / incidents_known_cause, 1)       AS change_share_pct,
       round(100.0 * change_related / incidents_known_cause
             - lag(100.0 * change_related / incidents_known_cause) OVER (ORDER BY quarter), 1) AS qoq_change_pp,
       change_breach_pct, other_breach_pct
FROM q
ORDER BY quarter;
