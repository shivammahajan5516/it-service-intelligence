-- =============================================================================
-- grants.sql  -  the API role can read ONLY the analytics layer (least privilege)
--   psql -v app_user=itsi_app -d it_service_intelligence -f database/grants.sql
-- =============================================================================
\set ON_ERROR_STOP on

SELECT format('REVOKE ALL ON SCHEMA staging, clean, audit FROM %I', :'app_user') \gexec
SELECT format('GRANT USAGE ON SCHEMA analytics TO %I', :'app_user') \gexec
SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO %I', :'app_user') \gexec
-- Analytics views read clean/audit tables; views run with the owner's rights,
-- so the app role does not need direct access to those schemas.
