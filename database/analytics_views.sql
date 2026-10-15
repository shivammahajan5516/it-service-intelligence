-- =============================================================================
-- analytics_views.sql  -  the single definition of every KPI population
--
-- analytics.fact_tickets (materialised) applies the business rules once:
--   * excludes possible duplicates (BR-RULE-01)
--   * defines SLA, duration, response, FCR and CSAT populations
--     (BR-RULE-04/06/07/08/09)
--   * flags repeat incidents (BR-RULE-10, window function)
-- Everything else (API, Power BI, SQL analysis, tests) reads from here.
-- Refresh after each load:  REFRESH MATERIALIZED VIEW analytics.fact_tickets;
-- =============================================================================
\set ON_ERROR_STOP on

DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;
COMMENT ON SCHEMA analytics IS 'Business-rule views: single definition of every KPI';

-- ---------------------------------------------------------------- dimensions
CREATE VIEW analytics.extract AS
SELECT snapshot_at, period_start, period_end FROM clean.extract_metadata;

CREATE VIEW analytics.dim_date AS
SELECT * FROM clean.calendar;

CREATE VIEW analytics.dim_team AS
SELECT t.team_id, t.team_name, t.support_tier, t.primary_location, t.operating_model,
       t.planned_headcount, t.team_lead_agent_id, l.agent_name AS team_lead_name
FROM clean.support_teams t
LEFT JOIN clean.agents l ON l.agent_id = t.team_lead_agent_id;

CREATE VIEW analytics.dim_agent AS
SELECT a.agent_id, a.agent_name, a.team_id, t.team_name, a.experience_level, a.shift,
       a.location, a.employment_type, a.start_date
FROM clean.agents a
JOIN clean.support_teams t USING (team_id);

CREATE VIEW analytics.dim_customer AS
SELECT customer_id, customer_name, industry, company_size, region, contract_type, sla_level,
       customer_since, customer_success_manager, is_placeholder
FROM clean.customers;

CREATE VIEW analytics.dim_category AS
SELECT subcategory_id, category_id, category, subcategory, default_team_id, complexity_tier,
       is_service_request
FROM clean.incident_categories;

CREATE VIEW analytics.dim_sla_target AS
SELECT * FROM clean.sla_targets;

-- ---------------------------------------------------------------- fact
CREATE MATERIALIZED VIEW analytics.fact_tickets AS
WITH base AS (
    SELECT t.*,
           c.is_placeholder                                        AS customer_is_placeholder,
           ic.complexity_tier,
           CASE WHEN ic.is_service_request IS NOT NULL THEN NOT ic.is_service_request
                WHEN t.root_cause = 'Service Request' THEN FALSE
                ELSE TRUE END                                      AS is_incident,
           t.ticket_status IN ('New', 'In Progress', 'Pending Customer', 'On Hold') AS is_open,
           t.ticket_status IN ('Resolved', 'Closed')               AS is_resolved,
           t.ticket_status = 'Cancelled'                           AS is_cancelled,
           (cal.is_weekend OR cal.is_uk_bank_holiday
             OR extract(hour FROM t.created_at) < 8
             OR extract(hour FROM t.created_at) >= 18)             AS is_out_of_hours
    FROM clean.tickets t
    JOIN clean.customers c        ON c.customer_id = t.customer_id
    JOIN clean.calendar  cal      ON cal.date = t.created_date
    LEFT JOIN clean.incident_categories ic ON ic.subcategory_id = t.subcategory_id
    WHERE NOT t.is_possible_duplicate                                -- BR-RULE-01
), pop AS (
    SELECT b.*,
           -- BR-RULE-04 / 06: SLA population
           (b.is_resolved AND NOT b.is_invalid_timestamp
             AND b.sla_target_hours IS NOT NULL)                   AS in_sla_population,
           -- first-response population
           (b.first_response_at IS NOT NULL AND NOT b.is_invalid_timestamp
             AND b.response_target_hours IS NOT NULL)              AS in_response_population,
           -- BR-RULE-09: FCR population
           (b.is_resolved AND b.first_contact_resolution IS NOT NULL
             AND NOT b.is_fcr_contradictory)                       AS in_fcr_population,
           -- BR-RULE-10: repeat incident (same customer + subcategory within 30 days)
           CASE WHEN b.is_incident AND NOT b.customer_is_placeholder AND b.subcategory_id IS NOT NULL
                THEN COALESCE(b.created_at - lag(b.created_at) OVER (
                         PARTITION BY b.customer_id, b.subcategory_id, b.is_incident
                         ORDER BY b.created_at, b.ticket_id) <= interval '30 days', FALSE)
           END                                                     AS is_repeat_incident
    FROM base b
)
SELECT
    p.ticket_id, p.customer_id, p.agent_id, p.team_id, p.created_at, p.created_date,
    date_trunc('month', p.created_at)::date                         AS created_month,
    p.first_response_at, p.resolved_at, p.priority, p.category, p.subcategory_id, p.subcategory,
    p.complexity_tier, p.channel, p.ticket_status, p.sla_level, p.sla_target_hours,
    p.response_target_hours, p.first_response_time_hours, p.resolution_time_hours,
    p.escalation_flag, p.reopened_count, (p.reopened_count > 0)     AS is_reopened,
    p.first_contact_resolution, p.customer_satisfaction, p.root_cause, p.resolution_type,
    p.business_impact, p.knowledge_base_used, p.region,
    p.is_incident, p.is_open, p.is_resolved, p.is_cancelled, p.is_out_of_hours,
    p.customer_is_placeholder,
    -- populations
    p.in_sla_population,
    (p.in_sla_population AND NOT p.is_resolution_outlier)           AS in_duration_population,
    p.in_response_population,
    p.in_fcr_population,
    (p.customer_satisfaction IS NOT NULL)                           AS has_valid_csat,
    -- outcomes (NULL outside their population so AVG() ignores them)
    CASE WHEN p.in_sla_population
         THEN p.resolution_time_hours > p.sla_target_hours END      AS sla_breached,
    CASE WHEN p.in_response_population
         THEN p.first_response_time_hours <= p.response_target_hours END AS response_sla_met,
    CASE WHEN p.in_fcr_population THEN p.first_contact_resolution END AS fcr_achieved,
    p.is_repeat_incident,
    -- backlog at snapshot
    CASE WHEN p.is_open
         THEN round(extract(epoch FROM (SELECT snapshot_at FROM clean.extract_metadata)
                                      - p.created_at) / 3600.0, 1) END AS open_age_hours,
    CASE WHEN p.is_open
         THEN extract(epoch FROM (SELECT snapshot_at FROM clean.extract_metadata) - p.created_at)
              / 3600.0 > p.sla_target_hours END                     AS is_open_past_target,
    -- data-quality context
    p.is_resolution_outlier, p.is_invalid_timestamp, p.is_orphan_customer,
    p.is_agent_team_mismatch, p.dq_issue_count
FROM pop p;

CREATE UNIQUE INDEX ux_fact_ticket_id   ON analytics.fact_tickets (ticket_id);
CREATE INDEX ix_fact_created_at         ON analytics.fact_tickets (created_at);
CREATE INDEX ix_fact_team_created       ON analytics.fact_tickets (team_id, created_at);
CREATE INDEX ix_fact_customer           ON analytics.fact_tickets (customer_id);
CREATE INDEX ix_fact_filters            ON analytics.fact_tickets (priority, category, region);

COMMENT ON MATERIALIZED VIEW analytics.fact_tickets IS
  'One row per valid ticket (duplicates removed). Populations and outcomes follow docs/05_business_rules.md.';

-- ---------------------------------------------------------------- KPI views
-- Headline KPIs (KPI-01..12) over the whole extract
CREATE VIEW analytics.kpi_overall AS
SELECT
    count(*)                                                                   AS total_tickets,
    count(*) FILTER (WHERE is_open)                                            AS open_tickets,
    count(*) FILTER (WHERE in_sla_population)                                  AS sla_population,
    round(100 * avg(sla_breached::int), 2)                                     AS sla_breach_pct,
    round(100 - 100 * avg(sla_breached::int), 2)                               AS sla_compliance_pct,
    round(avg(resolution_time_hours) FILTER (WHERE in_duration_population), 2) AS mean_resolution_hours,
    round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
           FILTER (WHERE in_duration_population))::numeric, 2)                 AS median_resolution_hours,
    round((percentile_cont(0.9) WITHIN GROUP (ORDER BY resolution_time_hours)
           FILTER (WHERE in_duration_population))::numeric, 2)                 AS p90_resolution_hours,
    round(100 * avg(response_sla_met::int), 2)                                 AS response_sla_met_pct,
    round(100 * avg(fcr_achieved::int), 2)                                     AS fcr_pct,
    round(100 * avg(is_reopened::int) FILTER (WHERE is_resolved), 2)           AS reopen_pct,
    round(100 * avg(escalation_flag::int), 2)                                  AS escalation_pct,
    round(avg(customer_satisfaction), 3)                                       AS avg_csat,
    count(customer_satisfaction)                                               AS csat_responses,
    round(100.0 * count(customer_satisfaction)
          / NULLIF(count(*) FILTER (WHERE is_resolved), 0), 2)                 AS csat_response_pct,
    round(100 * avg(is_repeat_incident::int), 2)                               AS repeat_incident_pct
FROM analytics.fact_tickets;

-- Monthly trend (KPI-03, 05, 07, 08, 09, 10)
CREATE VIEW analytics.kpi_monthly AS
SELECT
    created_month,
    count(*)                                                                   AS tickets,
    count(*) FILTER (WHERE is_resolved)                                        AS resolved,
    round(100 * avg(sla_breached::int), 2)                                     AS sla_breach_pct,
    round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
           FILTER (WHERE in_duration_population))::numeric, 2)                 AS median_resolution_hours,
    round(avg(resolution_time_hours) FILTER (WHERE in_duration_population), 2) AS mean_resolution_hours,
    round(100 * avg(fcr_achieved::int), 2)                                     AS fcr_pct,
    round(100 * avg(is_reopened::int) FILTER (WHERE is_resolved), 2)           AS reopen_pct,
    round(100 * avg(escalation_flag::int), 2)                                  AS escalation_pct,
    round(avg(customer_satisfaction), 3)                                       AS avg_csat,
    count(customer_satisfaction)                                               AS csat_responses,
    round(100 * avg(is_repeat_incident::int), 2)                               AS repeat_incident_pct
FROM analytics.fact_tickets
GROUP BY created_month;

-- Team scorecard (KPI-03, 05, 07, 08, 10, 13)
CREATE VIEW analytics.kpi_team AS
WITH months AS (
    SELECT count(DISTINCT created_month) AS n FROM analytics.fact_tickets
)
SELECT
    t.team_id, t.team_name, t.support_tier, t.planned_headcount,
    count(f.*)                                                                 AS tickets,
    round(count(f.*)::numeric / t.planned_headcount / (SELECT n FROM months), 2) AS tickets_per_agent_per_month,
    round(100 * avg(f.sla_breached::int), 2)                                   AS sla_breach_pct,
    round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)
           FILTER (WHERE f.in_duration_population))::numeric, 2)               AS median_resolution_hours,
    round(100 * avg(f.fcr_achieved::int), 2)                                   AS fcr_pct,
    round(100 * avg(f.is_reopened::int) FILTER (WHERE f.is_resolved), 2)      AS reopen_pct,
    round(100 * avg(f.escalation_flag::int), 2)                                AS escalation_pct,
    round(avg(f.customer_satisfaction), 3)                                     AS avg_csat,
    count(f.customer_satisfaction)                                             AS csat_responses,
    count(*) FILTER (WHERE f.is_open)                                          AS open_tickets
FROM analytics.dim_team t
LEFT JOIN analytics.fact_tickets f ON f.team_id = t.team_id
GROUP BY t.team_id, t.team_name, t.support_tier, t.planned_headcount;

-- SLA by priority (KPI-03, KPI-14)
CREATE VIEW analytics.kpi_priority AS
SELECT priority,
       count(*)                                                                AS tickets,
       count(*) FILTER (WHERE in_sla_population)                               AS sla_population,
       round(100 * avg(sla_breached::int), 2)                                  AS sla_breach_pct,
       round(100 * avg(response_sla_met::int), 2)                              AS response_sla_met_pct,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
              FILTER (WHERE in_duration_population))::numeric, 2)              AS median_resolution_hours
FROM analytics.fact_tickets
GROUP BY priority;

-- Root-cause Pareto, incidents with a known root cause (BR-RULE-11, KPI-15)
CREATE VIEW analytics.root_cause_pareto AS
WITH rc AS (
    SELECT root_cause, count(*) AS incidents,
           round(100 * avg(sla_breached::int), 2) AS sla_breach_pct,
           round((percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)
                  FILTER (WHERE in_duration_population))::numeric, 2) AS median_resolution_hours
    FROM analytics.fact_tickets
    WHERE is_incident AND is_resolved AND root_cause IS NOT NULL
    GROUP BY root_cause
)
SELECT root_cause, incidents, sla_breach_pct, median_resolution_hours,
       round(100.0 * incidents / sum(incidents) OVER (), 2)                    AS pct_of_incidents,
       round(100.0 * sum(incidents) OVER (ORDER BY incidents DESC, root_cause)
             / sum(incidents) OVER (), 2)                                      AS cumulative_pct,
       rank() OVER (ORDER BY incidents DESC)                                   AS rank
FROM rc;

-- Customer summary, all time (customer-level analysis excludes the Unknown placeholder)
CREATE VIEW analytics.customer_summary AS
SELECT c.customer_id, c.customer_name, c.industry, c.company_size, c.region, c.sla_level,
       c.contract_type, c.customer_success_manager,
       count(f.*)                                                              AS tickets,
       count(*) FILTER (WHERE f.is_incident)                                   AS incidents,
       count(*) FILTER (WHERE f.is_repeat_incident)                            AS repeat_incidents,
       round(100 * avg(f.is_repeat_incident::int), 2)                          AS repeat_incident_pct,
       round(100 * avg(f.sla_breached::int), 2)                                AS sla_breach_pct,
       round(avg(f.customer_satisfaction), 2)                                  AS avg_csat,
       count(f.customer_satisfaction)                                          AS csat_responses,
       count(*) FILTER (WHERE f.escalation_flag)                               AS escalations,
       count(*) FILTER (WHERE f.is_open)                                       AS open_tickets
FROM analytics.dim_customer c
JOIN analytics.fact_tickets f ON f.customer_id = c.customer_id
WHERE NOT c.is_placeholder
GROUP BY c.customer_id, c.customer_name, c.industry, c.company_size, c.region, c.sla_level,
         c.contract_type, c.customer_success_manager;

-- At-risk customers, last 90 days before the snapshot (BR-RULE-14, KPI-16)
CREATE VIEW analytics.customer_risk AS
WITH window_tickets AS (
    SELECT f.*
    FROM analytics.fact_tickets f
    WHERE f.created_at > (SELECT snapshot_at FROM clean.extract_metadata) - interval '90 days'
      AND NOT f.customer_is_placeholder
), company AS (
    SELECT avg(sla_breached::int) AS breach_rate FROM window_tickets
), per_customer AS (
    SELECT customer_id,
           count(*) FILTER (WHERE is_resolved)               AS resolved_tickets,
           avg(sla_breached::int)                            AS breach_rate,
           avg(is_repeat_incident::int)                      AS repeat_rate,
           avg(customer_satisfaction)                        AS avg_csat,
           count(customer_satisfaction)                      AS csat_responses
    FROM window_tickets
    GROUP BY customer_id
)
SELECT p.customer_id, c.customer_name, c.sla_level, c.customer_success_manager,
       p.resolved_tickets,
       round(100 * p.breach_rate, 1)                         AS sla_breach_pct_90d,
       round(100 * p.repeat_rate, 1)                         AS repeat_incident_pct_90d,
       round(p.avg_csat, 2)                                  AS avg_csat_90d,
       p.csat_responses                                      AS csat_responses_90d,
       (p.breach_rate >= 1.5 * co.breach_rate)               AS flag_high_breach,
       (p.repeat_rate >= 0.20)                               AS flag_repeat_incidents,
       (p.avg_csat <= 3.5 AND p.csat_responses >= 5)         AS flag_low_csat,
       ( (p.breach_rate >= 1.5 * co.breach_rate)::int
       + (p.repeat_rate >= 0.20)::int
       + COALESCE((p.avg_csat <= 3.5 AND p.csat_responses >= 5)::int, 0) ) AS risk_flags,
       (p.resolved_tickets >= 10 AND
        ( (p.breach_rate >= 1.5 * co.breach_rate)::int
        + (p.repeat_rate >= 0.20)::int
        + COALESCE((p.avg_csat <= 3.5 AND p.csat_responses >= 5)::int, 0) ) >= 2) AS is_at_risk
FROM per_customer p
JOIN clean.customers c USING (customer_id)
CROSS JOIN company co;

-- Open backlog at snapshot (KPI-02, KPI-18)
CREATE VIEW analytics.open_backlog AS
SELECT team_id, priority, count(*) AS open_tickets,
       count(*) FILTER (WHERE is_open_past_target) AS open_past_target,
       round(avg(open_age_hours), 1) AS avg_age_hours,
       max(open_age_hours) AS max_age_hours
FROM analytics.fact_tickets
WHERE is_open
GROUP BY team_id, priority;

-- Data-quality summary for the dashboard / report (KPI-19)
CREATE VIEW analytics.dq_summary AS
SELECT rule_id, issue, action, count(*) AS records
FROM audit.dq_issues
GROUP BY rule_id, issue, action;

-- Ticket-level investigation list
CREATE VIEW analytics.dq_investigation AS
SELECT d.record_id AS ticket_id, d.rule_id, d.issue, d.action, d.detail
FROM audit.dq_issues d
WHERE d.table_name = 'clean.tickets'
  AND d.rule_id IN ('BR-RULE-06', 'BR-RULE-08', 'BR-RULE-09', 'BR-RULE-13', 'R04', 'F03', 'F04');
