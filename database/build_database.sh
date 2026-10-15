#!/usr/bin/env bash
# Build the whole PostgreSQL layer from the CSVs in data/raw/ (macOS / Linux / WSL).
#   bash database/build_database.sh
# Reads connection settings from .env (see .env.example). Re-runnable.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  # strip Windows line endings if the file was edited on Windows
  set -a; . <(sed 's/\r$//' .env); set +a
fi
DB_HOST="${DB_HOST:-localhost}"; DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-it_service_intelligence}"
DB_APP_USER="${DB_APP_USER:-itsi_app}"
: "${DB_APP_PASSWORD:?Set DB_APP_PASSWORD in .env}"

command -v psql >/dev/null || { echo "ERROR: psql not found - install PostgreSQL (docs/SETUP.md)"; exit 1; }

export PGHOST="$DB_HOST" PGPORT="$DB_PORT"
[ -n "${DB_ADMIN_USER:-}" ] && export PGUSER="$DB_ADMIN_USER"
[ -n "${DB_ADMIN_PASSWORD:-}" ] && export PGPASSWORD="$DB_ADMIN_PASSWORD"
PSQL=(psql -X -q -v ON_ERROR_STOP=1)

echo "== 1/11 Database and read-only role"
"${PSQL[@]}" -d postgres -v db_name="$DB_NAME" -v app_user="$DB_APP_USER" \
  -v app_password="$DB_APP_PASSWORD" -f database/setup_roles.sql

step=2
for f in schema load_staging transform_clean constraints indexes analytics_views powerbi_views; do
  echo "== ${step}/11 ${f}.sql"
  "${PSQL[@]}" -d "$DB_NAME" -f "database/${f}.sql" >/dev/null
  step=$((step + 1))
done

echo "== 9/11 grants.sql"
"${PSQL[@]}" -d "$DB_NAME" -v app_user="$DB_APP_USER" -f database/grants.sql >/dev/null

echo "== 10/11 checks.sql"
psql -X -v ON_ERROR_STOP=1 -d "$DB_NAME" -f database/checks.sql

echo "== 11/11 export_analytics.sql -> data/processed/"
mkdir -p data/processed
"${PSQL[@]}" -d "$DB_NAME" -f database/export_analytics.sql

echo "Database '${DB_NAME}' built. API/Power BI user: ${DB_APP_USER} (read-only, analytics schema)."
