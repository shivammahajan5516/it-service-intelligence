-- =============================================================================
-- export_analytics.sql  -  analytics layer -> data/processed/*.csv
--
-- The Python analysis (analytics/) and anyone without PostgreSQL can work from
-- these files. They are the SAME rows the API and Power BI use, so every tool
-- shares one set of business rules. Run from the project root (build scripts
-- call it automatically).
-- =============================================================================
\copy (SELECT * FROM analytics.fact_tickets ORDER BY ticket_id) TO 'data/processed/fact_tickets.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.dim_customer ORDER BY customer_id) TO 'data/processed/dim_customer.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.dim_agent ORDER BY agent_id) TO 'data/processed/dim_agent.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.dim_team ORDER BY team_id) TO 'data/processed/dim_team.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.dim_category ORDER BY subcategory_id) TO 'data/processed/dim_category.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.dim_date ORDER BY date) TO 'data/processed/dim_date.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.dim_sla_target ORDER BY sla_rule_id) TO 'data/processed/dim_sla_target.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM audit.dq_issues ORDER BY issue_id) TO 'data/processed/dq_issues.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.pbi_fact_tickets ORDER BY ticket_id) TO 'data/processed/pbi_fact_tickets.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM analytics.pbi_customer_risk ORDER BY customer_id) TO 'data/processed/pbi_customer_risk.csv' WITH (FORMAT csv, HEADER true)
