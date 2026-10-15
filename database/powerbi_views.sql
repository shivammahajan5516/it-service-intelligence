-- =============================================================================
-- powerbi_views.sql  -  Power BI-friendly views on top of the analytics layer
--
-- Same rows and rules as analytics.fact_tickets; flags are exposed as 0/1
-- integers (NULL = outside the population) so DAX measures stay simple and
-- match the SQL KPIs exactly. Also adds resolved_date for the inactive
-- relationship to the date table.
-- =============================================================================
\set ON_ERROR_STOP on

CREATE OR REPLACE VIEW analytics.pbi_fact_tickets AS
SELECT
    f.ticket_id, f.customer_id, f.agent_id, f.team_id, f.subcategory_id,
    f.created_at, f.created_date, f.resolved_at::date AS resolved_date, f.created_month,
    f.priority, f.category, f.subcategory, f.complexity_tier, f.channel, f.ticket_status,
    f.sla_level, f.region, f.root_cause, f.resolution_type, f.business_impact,
    f.sla_target_hours, f.response_target_hours, f.first_response_time_hours,
    f.resolution_time_hours, f.reopened_count, f.customer_satisfaction, f.open_age_hours,
    f.is_incident::int            AS is_incident,
    f.is_open::int                AS is_open,
    f.is_resolved::int            AS is_resolved,
    f.is_cancelled::int           AS is_cancelled,
    f.is_out_of_hours::int        AS is_out_of_hours,
    f.escalation_flag::int        AS is_escalated,
    f.is_reopened::int            AS is_reopened,
    f.knowledge_base_used::int    AS kb_used,
    f.in_sla_population::int      AS in_sla_population,
    f.in_duration_population::int AS in_duration_population,
    f.in_response_population::int AS in_response_population,
    f.in_fcr_population::int      AS in_fcr_population,
    f.sla_breached::int           AS sla_breached,
    f.response_sla_met::int       AS response_sla_met,
    f.fcr_achieved::int           AS fcr_achieved,
    f.is_repeat_incident::int     AS is_repeat_incident,
    f.is_open_past_target::int    AS is_open_past_target,
    f.customer_is_placeholder::int AS customer_is_placeholder
FROM analytics.fact_tickets f;

CREATE OR REPLACE VIEW analytics.pbi_customer_risk AS
SELECT customer_id, resolved_tickets, sla_breach_pct_90d, repeat_incident_pct_90d, avg_csat_90d,
       csat_responses_90d, flag_high_breach::int AS flag_high_breach,
       flag_repeat_incidents::int AS flag_repeat_incidents, COALESCE(flag_low_csat, FALSE)::int AS flag_low_csat,
       risk_flags, is_at_risk::int AS is_at_risk
FROM analytics.customer_risk;

COMMENT ON VIEW analytics.pbi_fact_tickets IS 'Power BI fact table: analytics.fact_tickets with 0/1 flags';
