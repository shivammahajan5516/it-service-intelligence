-- =============================================================================
-- load_staging.sql  -  Raw CSV -> staging.*  (client-side \copy)
--
-- Run with psql FROM THE PROJECT ROOT (paths are relative to it):
--     psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/load_staging.sql
-- \copy reads the files on the machine running psql, so the database server
-- does not need access to your project folder (works for local and cloud DBs).
-- =============================================================================

TRUNCATE staging.tickets, staging.customers, staging.agents, staging.support_teams,
         staging.sla_targets, staging.calendar, staging.incident_categories;

\copy staging.support_teams       FROM 'data/raw/support_teams.csv'       WITH (FORMAT csv, HEADER true, NULL '')
\copy staging.agents              FROM 'data/raw/agents.csv'              WITH (FORMAT csv, HEADER true, NULL '')
\copy staging.customers           FROM 'data/raw/customers.csv'           WITH (FORMAT csv, HEADER true, NULL '')
\copy staging.sla_targets         FROM 'data/raw/sla_targets.csv'         WITH (FORMAT csv, HEADER true, NULL '')
\copy staging.calendar            FROM 'data/raw/calendar.csv'            WITH (FORMAT csv, HEADER true, NULL '')
\copy staging.incident_categories FROM 'data/raw/incident_categories.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy staging.tickets             FROM 'data/raw/tickets.csv'             WITH (FORMAT csv, HEADER true, NULL '')

INSERT INTO audit.load_log (step, table_name, row_count)
SELECT 'load_staging', t, n FROM (
    SELECT 'staging.tickets' AS t, count(*) AS n FROM staging.tickets
    UNION ALL SELECT 'staging.customers', count(*) FROM staging.customers
    UNION ALL SELECT 'staging.agents', count(*) FROM staging.agents
    UNION ALL SELECT 'staging.support_teams', count(*) FROM staging.support_teams
    UNION ALL SELECT 'staging.sla_targets', count(*) FROM staging.sla_targets
    UNION ALL SELECT 'staging.calendar', count(*) FROM staging.calendar
    UNION ALL SELECT 'staging.incident_categories', count(*) FROM staging.incident_categories
) s;

SELECT table_name, row_count FROM audit.load_log WHERE step = 'load_staging' ORDER BY log_id;
