-- =============================================================================
-- transform_clean.sql  -  staging.* -> clean.*
--
-- Applies the business rules in docs/05_business_rules.md (BR-RULE-xx).
-- Every correction or exclusion is recorded in audit.dq_issues, so nothing is
-- changed silently and every KPI exclusion can be traced to a rule.
-- =============================================================================
\set ON_ERROR_STOP on
BEGIN;

TRUNCATE clean.tickets, clean.customers, clean.agents, clean.support_teams, clean.sla_targets,
         clean.calendar, clean.incident_categories, clean.category_label_map,
         clean.extract_metadata;
TRUNCATE audit.dq_issues;

INSERT INTO clean.extract_metadata (extract_name, snapshot_at, period_start, period_end)
VALUES ('Northbridge ITSM extract (synthetic)', '2025-12-31 23:59:59', '2024-01-01', '2025-12-31');

-- -----------------------------------------------------------------------------
-- 1. Reference / dimension tables
-- -----------------------------------------------------------------------------
INSERT INTO clean.support_teams
SELECT trim(team_id), trim(team_name), trim(support_tier), trim(primary_location),
       trim(operating_model), planned_headcount::integer, NULLIF(trim(team_lead_agent_id), '')
FROM staging.support_teams;

INSERT INTO clean.agents
SELECT trim(agent_id), trim(agent_name), trim(team_id), trim(experience_level),
       NULLIF(trim(shift), ''), trim(location), trim(employment_type), start_date::date
FROM staging.agents;

INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action)
SELECT 'clean.agents', agent_id, 'M01', 'shift missing', 'kept NULL'
FROM clean.agents WHERE shift IS NULL;

INSERT INTO clean.customers
SELECT trim(customer_id), trim(customer_name), COALESCE(NULLIF(trim(industry), ''), 'Unknown'),
       trim(company_size), trim(region), trim(contract_type), trim(sla_level),
       customer_since::date, NULLIF(trim(customer_success_manager), ''), FALSE
FROM staging.customers;

INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action)
SELECT 'clean.customers', customer_id, 'M01', 'industry missing', 'set to Unknown'
FROM staging.customers WHERE NULLIF(trim(industry), '') IS NULL;

-- Placeholder for tickets whose customer_id is not in the customer master (BR-RULE-13)
INSERT INTO clean.customers (customer_id, customer_name, industry, company_size, region,
                             contract_type, sla_level, customer_since, customer_success_manager,
                             is_placeholder)
VALUES ('CUST-UNKNOWN', 'Unknown customer', 'Unknown', 'Unknown', 'Unknown', 'Unknown',
        NULL, NULL, NULL, TRUE);

INSERT INTO clean.sla_targets
SELECT trim(sla_rule_id), trim(sla_level), trim(priority), response_target_hours::numeric,
       resolution_target_hours::numeric, trim(clock_basis), effective_from::date,
       NULLIF(trim(effective_to), '')::date
FROM staging.sla_targets;

INSERT INTO clean.calendar
SELECT date::date, date_key::integer, year::smallint, quarter::smallint, month::smallint,
       month_name, year_month, date_trunc('month', date::date)::date, iso_year::smallint,
       iso_week::smallint, day_of_month::smallint, day_of_week::smallint, day_name,
       clean.try_bool(is_weekend), clean.try_bool(is_uk_bank_holiday), NULLIF(holiday_name, ''),
       clean.try_bool(is_working_day), fiscal_year, fiscal_quarter::smallint
FROM staging.calendar;

INSERT INTO clean.incident_categories
SELECT trim(subcategory_id), trim(category_id), trim(category), trim(subcategory),
       trim(default_team_id), trim(complexity_tier), clean.try_bool(is_service_request)
FROM staging.incident_categories;

-- -----------------------------------------------------------------------------
-- 2. Category label standardisation (BR-RULE-12)
--    exact -> normalised (case, punctuation, 'and' vs '&') -> explicit synonym
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE controlled AS
SELECT DISTINCT category,
       regexp_replace(replace(lower(category), ' and ', ' '), '[^a-z]', '', 'g') AS norm
FROM clean.incident_categories;

CREATE TEMP TABLE synonyms (raw_label text, category text);
INSERT INTO synonyms VALUES
    ('Netwrk', 'Network'), ('H/W', 'Hardware'), ('SW', 'Software'), ('Infra', 'Infrastructure'),
    ('Cloud', 'Cloud Services'), ('Business Apps', 'Business Applications'),
    ('Cyber Security', 'Security'), ('DB', 'Database');

INSERT INTO clean.category_label_map (raw_label, category, match_type)
SELECT l.raw_label,
       COALESCE(e.category, n.category, s.category),
       CASE WHEN e.category IS NOT NULL THEN 'exact'
            WHEN n.category IS NOT NULL THEN 'normalised'
            WHEN s.category IS NOT NULL THEN 'synonym' END
FROM (SELECT DISTINCT category AS raw_label FROM staging.tickets) l
LEFT JOIN controlled e ON e.category = l.raw_label
LEFT JOIN controlled n ON n.norm = regexp_replace(replace(lower(l.raw_label), ' and ', ' '), '[^a-z]', '', 'g')
LEFT JOIN synonyms   s ON s.raw_label = l.raw_label
WHERE COALESCE(e.category, n.category, s.category) IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 3. Tickets: collapse exact duplicate rows (BR-RULE-01), type and standardise
-- -----------------------------------------------------------------------------
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'D01', 'exact duplicate row in extract', 'collapsed to one row',
       count(*) || ' identical rows'
FROM staging.tickets s
GROUP BY ticket_id, md5(s::text)
HAVING count(*) > 1;

INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action)
SELECT 'clean.tickets', ticket_id, 'D02', 'ticket_id reused with different content',
       'kept earliest created_at version'
FROM staging.tickets s
GROUP BY ticket_id
HAVING count(DISTINCT md5(s::text)) > 1;

INSERT INTO clean.tickets (
    ticket_id, source_row_count, customer_id, source_customer_id, agent_id, team_id,
    created_at, first_response_at, resolved_at, priority, category, category_raw,
    subcategory_id, subcategory, channel, ticket_status, sla_target_hours, sla_target_source,
    first_response_time_hours, resolution_time_hours, escalation_flag, reopened_count,
    first_contact_resolution, customer_satisfaction, customer_satisfaction_raw, root_cause,
    resolution_type, business_impact, knowledge_base_used, region, region_raw)
SELECT
    d.ticket_id,
    d.n_rows,
    trim(d.customer_id),
    trim(d.customer_id),
    NULLIF(trim(d.agent_id), ''),
    trim(d.team_id),
    d.created_ts,
    d.fr_ts,
    d.res_ts,
    upper(trim(d.priority)),
    COALESCE(m.category, ic.category, 'Unknown'),
    d.category,
    ic.subcategory_id,
    NULLIF(trim(d.subcategory), ''),
    NULLIF(trim(d.channel), ''),
    trim(d.ticket_status),
    clean.try_numeric(d.sla_target_hours),
    CASE WHEN clean.try_numeric(d.sla_target_hours) IS NOT NULL THEN 'source' END,
    round(extract(epoch FROM d.fr_ts - d.created_ts) / 3600.0, 2),
    round(extract(epoch FROM d.res_ts - d.created_ts) / 3600.0, 2),
    COALESCE(clean.try_bool(d.escalation_flag), FALSE),
    COALESCE(clean.try_numeric(d.reopened_count), 0)::smallint,
    clean.try_bool(d.first_contact_resolution),
    CASE WHEN clean.try_numeric(d.customer_satisfaction) IN (1, 2, 3, 4, 5)
         THEN clean.try_numeric(d.customer_satisfaction)::smallint END,
    clean.try_numeric(d.customer_satisfaction),
    NULLIF(trim(d.root_cause), ''),
    NULLIF(trim(d.resolution_type), ''),
    trim(d.business_impact),
    clean.try_bool(d.knowledge_base_used),
    COALESCE(r.region, 'Unknown'),
    d.region
FROM (
    SELECT DISTINCT ON (s.ticket_id)
           s.*,
           count(*) OVER (PARTITION BY s.ticket_id) AS n_rows,
           clean.try_timestamp(s.created_at)        AS created_ts,
           clean.try_timestamp(s.first_response_at) AS fr_ts,
           clean.try_timestamp(s.resolved_at)       AS res_ts
    FROM staging.tickets s
    ORDER BY s.ticket_id, clean.try_timestamp(s.created_at)
) d
LEFT JOIN clean.category_label_map m ON m.raw_label = d.category
LEFT JOIN clean.incident_categories ic ON ic.subcategory = trim(d.subcategory)
LEFT JOIN (SELECT DISTINCT region FROM clean.customers WHERE NOT is_placeholder) r
       ON lower(r.region) = lower(trim(d.region));

-- -----------------------------------------------------------------------------
-- 4. Row-level data-quality rules. Each block flags rows AND logs the issue.
-- -----------------------------------------------------------------------------

-- V01 / BR-RULE-12: category label standardised
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', t.ticket_id, 'BR-RULE-12', 'non-standard category label',
       'mapped to controlled category', t.category_raw || ' -> ' || t.category
FROM clean.tickets t WHERE t.category_raw IS DISTINCT FROM t.category;

-- V04: region label standardised
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'V04', 'non-standard region label', 'standardised',
       quote_literal(region_raw) || ' -> ' || region
FROM clean.tickets WHERE region_raw IS DISTINCT FROM region;

-- R01 / BR-RULE-13: orphan customer
WITH u AS (
    UPDATE clean.tickets t SET customer_id = 'CUST-UNKNOWN', is_orphan_customer = TRUE
    WHERE NOT EXISTS (SELECT 1 FROM clean.customers c WHERE c.customer_id = t.customer_id)
    RETURNING t.ticket_id, t.source_customer_id)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'BR-RULE-13', 'customer_id not in customer master',
       'assigned to CUST-UNKNOWN; excluded from customer analysis', source_customer_id
FROM u;

-- SLA level and targets; BR-RULE-15: derive missing target from the SLA rules
UPDATE clean.tickets t
SET sla_level = c.sla_level
FROM clean.customers c
WHERE c.customer_id = t.customer_id;

WITH u AS (
    UPDATE clean.tickets t
    SET sla_target_hours = s.resolution_target_hours, sla_target_source = 'derived'
    FROM clean.sla_targets s
    WHERE t.sla_target_hours IS NULL AND s.sla_level = t.sla_level AND s.priority = t.priority
    RETURNING t.ticket_id, s.resolution_target_hours)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'BR-RULE-15', 'sla_target_hours missing',
       'derived from sla_targets', resolution_target_hours::text || ' h'
FROM u;

UPDATE clean.tickets t
SET response_target_hours = s.response_target_hours
FROM clean.sla_targets s
WHERE s.sla_level = t.sla_level AND s.priority = t.priority;

-- F04: source target disagrees with SLA rule (logged, source value kept)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', t.ticket_id, 'F04', 'sla_target_hours differs from SLA rule',
       'source value kept', t.sla_target_hours || ' vs ' || s.resolution_target_hours
FROM clean.tickets t
JOIN clean.sla_targets s ON s.sla_level = t.sla_level AND s.priority = t.priority
WHERE t.sla_target_hours <> s.resolution_target_hours;

-- BR-RULE-06: invalid timestamps (kept for volume, excluded from duration/SLA KPIs)
WITH u AS (
    UPDATE clean.tickets SET is_invalid_timestamp = TRUE
    WHERE (resolved_at < created_at)
       OR (first_response_at < created_at)
       OR (first_response_at > resolved_at AND resolved_at >= created_at)
       OR (ticket_status IN ('Resolved', 'Closed') AND resolved_at IS NULL)
    RETURNING ticket_id, created_at, first_response_at, resolved_at, ticket_status)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'BR-RULE-06',
       CASE WHEN resolved_at < created_at THEN 'resolved_at before created_at'
            WHEN first_response_at < created_at THEN 'first_response_at before created_at'
            WHEN first_response_at > resolved_at THEN 'first_response_at after resolved_at'
            ELSE ticket_status || ' ticket without resolved_at' END,
       'excluded from duration and SLA KPIs', NULL
FROM u;

-- BR-RULE-08: resolution outliers (> 30 days or > 10x SLA target)
WITH u AS (
    UPDATE clean.tickets SET is_resolution_outlier = TRUE
    WHERE ticket_status IN ('Resolved', 'Closed') AND NOT is_invalid_timestamp
      AND (resolution_time_hours > 720 OR resolution_time_hours > 10 * sla_target_hours)
    RETURNING ticket_id, resolution_time_hours, sla_target_hours)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'BR-RULE-08', 'resolution time outlier',
       'counted in SLA breach rate, excluded from resolution-time averages',
       resolution_time_hours || ' h vs target ' || sla_target_hours || ' h'
FROM u;

-- BR-RULE-07: invalid CSAT
WITH u AS (
    UPDATE clean.tickets SET is_invalid_csat = TRUE
    WHERE customer_satisfaction_raw IS NOT NULL AND customer_satisfaction IS NULL
    RETURNING ticket_id, customer_satisfaction_raw)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'BR-RULE-07', 'customer_satisfaction outside 1-5',
       'treated as missing', customer_satisfaction_raw::text
FROM u;

-- BR-RULE-09: FCR contradicted by escalation or reopen
WITH u AS (
    UPDATE clean.tickets SET is_fcr_contradictory = TRUE
    WHERE first_contact_resolution AND (escalation_flag OR reopened_count > 0)
    RETURNING ticket_id, escalation_flag, reopened_count)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'BR-RULE-09', 'FCR = true contradicted',
       'excluded from FCR KPI',
       CASE WHEN escalation_flag THEN 'escalated' ELSE 'reopened ' || reopened_count || 'x' END
FROM u;

-- R04: agent does not belong to resolver team
WITH u AS (
    UPDATE clean.tickets t SET is_agent_team_mismatch = TRUE
    FROM clean.agents a
    WHERE a.agent_id = t.agent_id AND a.team_id <> t.team_id
    RETURNING t.ticket_id, t.agent_id, a.team_id AS agent_team, t.team_id)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'R04', 'agent not in ticket resolver team',
       'kept; listed for investigation', agent_id || ' (' || agent_team || ') on ' || team_id || ' ticket'
FROM u;

-- F03: P1 with Low business impact
WITH u AS (
    UPDATE clean.tickets SET is_priority_impact_mismatch = TRUE
    WHERE priority = 'P1' AND business_impact = 'Low'
    RETURNING ticket_id)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action)
SELECT 'clean.tickets', ticket_id, 'F03', 'P1 priority with Low business impact',
       'kept; listed for investigation'
FROM u;

-- BR-RULE-01: near-duplicates (same customer, subcategory, priority within 15 minutes)
WITH ordered AS (
    SELECT ticket_id, created_at,
           lag(ticket_id)  OVER w AS prev_ticket_id,
           lag(created_at) OVER w AS prev_created_at
    FROM clean.tickets
    WHERE subcategory IS NOT NULL
    WINDOW w AS (PARTITION BY source_customer_id, subcategory, priority
                 ORDER BY created_at, ticket_id)
), u AS (
    UPDATE clean.tickets t
    SET is_possible_duplicate = TRUE, duplicate_of_ticket_id = o.prev_ticket_id
    FROM ordered o
    WHERE o.ticket_id = t.ticket_id
      AND o.created_at - o.prev_created_at <= interval '15 minutes'
    RETURNING t.ticket_id, o.prev_ticket_id, o.created_at - o.prev_created_at AS gap)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action, detail)
SELECT 'clean.tickets', ticket_id, 'BR-RULE-01', 'possible duplicate of earlier ticket',
       'excluded from KPIs', prev_ticket_id || ' (' || gap || ' earlier)'
FROM u;

-- Missing optional values (logged only)
INSERT INTO audit.dq_issues (table_name, record_id, rule_id, issue, action)
SELECT 'clean.tickets', ticket_id, rule, issue, 'kept NULL; excluded where field is required'
FROM (
    SELECT ticket_id, 'M02' AS rule, 'root_cause missing on resolved ticket' AS issue
    FROM clean.tickets WHERE ticket_status IN ('Resolved', 'Closed') AND root_cause IS NULL
    UNION ALL
    SELECT ticket_id, 'M03', 'knowledge_base_used missing' FROM clean.tickets WHERE knowledge_base_used IS NULL
    UNION ALL
    SELECT ticket_id, 'M04', 'channel missing' FROM clean.tickets WHERE channel IS NULL
    UNION ALL
    SELECT ticket_id, 'M05', 'subcategory missing' FROM clean.tickets WHERE subcategory IS NULL
    UNION ALL
    SELECT ticket_id, 'R05', 'resolved ticket with no agent'
    FROM clean.tickets WHERE ticket_status IN ('Resolved', 'Closed') AND agent_id IS NULL
) m;

-- Number of data-quality flags per ticket (handy filter for investigation lists)
UPDATE clean.tickets
SET dq_issue_count = is_possible_duplicate::int + is_invalid_timestamp::int
                   + is_resolution_outlier::int + is_fcr_contradictory::int
                   + is_agent_team_mismatch::int + is_orphan_customer::int
                   + is_priority_impact_mismatch::int + is_invalid_csat::int;

INSERT INTO audit.load_log (step, table_name, row_count)
SELECT 'transform_clean', t, n FROM (
    SELECT 'clean.tickets' AS t, count(*) AS n FROM clean.tickets
    UNION ALL SELECT 'clean.customers', count(*) FROM clean.customers
    UNION ALL SELECT 'clean.agents', count(*) FROM clean.agents
    UNION ALL SELECT 'clean.support_teams', count(*) FROM clean.support_teams
    UNION ALL SELECT 'clean.sla_targets', count(*) FROM clean.sla_targets
    UNION ALL SELECT 'clean.calendar', count(*) FROM clean.calendar
    UNION ALL SELECT 'clean.incident_categories', count(*) FROM clean.incident_categories
    UNION ALL SELECT 'audit.dq_issues', count(*) FROM audit.dq_issues
) s;

COMMIT;

SELECT rule_id, issue, action, count(*) AS records
FROM audit.dq_issues GROUP BY rule_id, issue, action ORDER BY rule_id, records DESC;
