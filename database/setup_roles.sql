-- =============================================================================
-- setup_roles.sql  -  create the database and a READ-ONLY role for the API
--
-- Run once as a PostgreSQL superuser / admin, connected to the 'postgres' DB.
-- Passwords are passed in as psql variables (never stored in this file):
--
--   psql -v db_name=it_service_intelligence -v app_user=itsi_app \
--        -v app_password="$DB_APP_PASSWORD" -d postgres -f database/setup_roles.sql
--
-- The build scripts (build_database.sh / .ps1) do this for you from .env.
-- =============================================================================
\set ON_ERROR_STOP on

-- Read-only application role used by FastAPI and Power BI (NFR-04)
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec
-- Keep the password in sync if the role already existed
SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
\gexec

SELECT format('CREATE DATABASE %I', :'db_name')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name')
\gexec

SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db_name') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db_name', :'app_user') \gexec
