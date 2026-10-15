-- =============================================================================
-- checks.sql  -  post-build assertions. Fails (non-zero exit) if any is broken.
--   psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/checks.sql
-- =============================================================================
\set ON_ERROR_STOP on

CREATE TEMP TABLE check_results (check_id text, description text, expected text, actual text, passed boolean);

INSERT INTO check_results
-- Reconciliation: staging -> clean
SELECT 'C01', 'clean.tickets = distinct ticket_ids in staging',
       (SELECT count(DISTINCT ticket_id) FROM staging.tickets)::text,
       (SELECT count(*) FROM clean.tickets)::text,
       (SELECT count(DISTINCT ticket_id) FROM staging.tickets) = (SELECT count(*) FROM clean.tickets)
UNION ALL
SELECT 'C02', 'staging rows = clean rows + collapsed exact duplicates',
       (SELECT count(*) FROM staging.tickets)::text,
       (SELECT sum(source_row_count) FROM clean.tickets)::text,
       (SELECT count(*) FROM staging.tickets) = (SELECT sum(source_row_count) FROM clean.tickets)
UNION ALL
SELECT 'C03', 'fact_tickets = clean tickets minus possible duplicates',
       (SELECT count(*) FROM clean.tickets WHERE NOT is_possible_duplicate)::text,
       (SELECT count(*) FROM analytics.fact_tickets)::text,
       (SELECT count(*) FROM clean.tickets WHERE NOT is_possible_duplicate)
         = (SELECT count(*) FROM analytics.fact_tickets)
UNION ALL
SELECT 'C04', 'customers loaded (+1 Unknown placeholder)', '501',
       (SELECT count(*) FROM clean.customers)::text, (SELECT count(*) FROM clean.customers) = 501
UNION ALL
SELECT 'C05', 'every SLA level x priority has exactly one rule', '16',
       (SELECT count(DISTINCT (sla_level, priority)) FROM clean.sla_targets)::text,
       (SELECT count(DISTINCT (sla_level, priority)) FROM clean.sla_targets) = 16
UNION ALL
SELECT 'C06', 'no non-standard category labels left in clean', '0',
       (SELECT count(*) FROM clean.tickets t WHERE NOT EXISTS
            (SELECT 1 FROM clean.incident_categories c WHERE c.category = t.category))::text,
       NOT EXISTS (SELECT 1 FROM clean.tickets t WHERE NOT EXISTS
            (SELECT 1 FROM clean.incident_categories c WHERE c.category = t.category))
UNION ALL
SELECT 'C07', 'no negative durations in the duration population', '0',
       (SELECT count(*) FROM analytics.fact_tickets
         WHERE in_duration_population AND resolution_time_hours < 0)::text,
       NOT EXISTS (SELECT 1 FROM analytics.fact_tickets
                    WHERE in_duration_population AND resolution_time_hours < 0)
UNION ALL
SELECT 'C08', 'every ticket in the SLA population has a target', '0',
       (SELECT count(*) FROM analytics.fact_tickets
         WHERE in_sla_population AND sla_target_hours IS NULL)::text,
       NOT EXISTS (SELECT 1 FROM analytics.fact_tickets
                    WHERE in_sla_population AND sla_target_hours IS NULL)
UNION ALL
SELECT 'C09', 'breach + compliance = 100%', '100',
       (SELECT sla_breach_pct + sla_compliance_pct FROM analytics.kpi_overall)::text,
       (SELECT sla_breach_pct + sla_compliance_pct FROM analytics.kpi_overall) = 100
UNION ALL
SELECT 'C10', 'team tickets sum to total tickets',
       (SELECT total_tickets FROM analytics.kpi_overall)::text,
       (SELECT sum(tickets) FROM analytics.kpi_team)::text,
       (SELECT total_tickets FROM analytics.kpi_overall) = (SELECT sum(tickets) FROM analytics.kpi_team)
UNION ALL
SELECT 'C11', 'monthly tickets sum to total tickets',
       (SELECT total_tickets FROM analytics.kpi_overall)::text,
       (SELECT sum(tickets) FROM analytics.kpi_monthly)::text,
       (SELECT total_tickets FROM analytics.kpi_overall) = (SELECT sum(tickets) FROM analytics.kpi_monthly)
UNION ALL
SELECT 'C12', 'Pareto cumulative % ends at 100', '100.00',
       (SELECT max(cumulative_pct) FROM analytics.root_cause_pareto)::text,
       (SELECT max(cumulative_pct) FROM analytics.root_cause_pareto) = 100
UNION ALL
SELECT 'C13', 'every FCR-true ticket in FCR population is not escalated / reopened', '0',
       (SELECT count(*) FROM analytics.fact_tickets
         WHERE fcr_achieved AND (escalation_flag OR reopened_count > 0))::text,
       NOT EXISTS (SELECT 1 FROM analytics.fact_tickets
                    WHERE fcr_achieved AND (escalation_flag OR reopened_count > 0))
UNION ALL
SELECT 'C14', 'every CSAT value in clean is 1-5', '0',
       (SELECT count(*) FROM clean.tickets WHERE customer_satisfaction NOT BETWEEN 1 AND 5)::text,
       NOT EXISTS (SELECT 1 FROM clean.tickets WHERE customer_satisfaction NOT BETWEEN 1 AND 5)
UNION ALL
SELECT 'C15', 'every data-quality flag has an audit entry', '0',
       (SELECT count(*) FROM clean.tickets t WHERE t.dq_issue_count > 0 AND NOT EXISTS
            (SELECT 1 FROM audit.dq_issues d WHERE d.record_id = t.ticket_id))::text,
       NOT EXISTS (SELECT 1 FROM clean.tickets t WHERE t.dq_issue_count > 0 AND NOT EXISTS
            (SELECT 1 FROM audit.dq_issues d WHERE d.record_id = t.ticket_id));

SELECT check_id, description, expected, actual, CASE WHEN passed THEN 'PASS' ELSE 'FAIL' END AS status
FROM check_results ORDER BY check_id;

DO $$
DECLARE n int;
BEGIN
    SELECT count(*) INTO n FROM check_results WHERE NOT passed;
    IF n > 0 THEN
        RAISE EXCEPTION '% database check(s) failed - see table above', n;
    END IF;
    RAISE NOTICE 'All database checks passed';
END $$;
