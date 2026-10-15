#!/usr/bin/env bash
# Rebuild every analysis output from the database: SQL results, Python report, model, API docs, Power BI values.
# Requires the database to be built (database/build_database.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="${PYTHON:-python3}"; fi
"$PY" scripts/reconcile_db.py
"$PY" scripts/run_sql_analysis.py --strict
"$PY" analytics/run_analysis.py
"$PY" analytics/model.py
"$PY" powerbi/expected_values.py
"$PY" scripts/generate_api_docs.py
echo "All analysis outputs regenerated."
