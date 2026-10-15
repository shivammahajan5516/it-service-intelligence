#!/usr/bin/env bash
# One-time setup for macOS / Linux / WSL / GitHub Codespaces.
#   bash scripts/setup.sh
# Creates .venv, installs Python dependencies, builds and validates the dataset, runs tests.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: $PY not found. Install Python 3.11+ (see docs/SETUP.md)." >&2
  exit 1
fi
"$PY" - <<'EOF'
import sys
if sys.version_info < (3, 11):
    sys.exit(f"ERROR: Python 3.11+ required, found {sys.version.split()[0]}")
print(f"Python {sys.version.split()[0]} OK")
EOF

if [ ! -d .venv ]; then
  echo "== Creating virtual environment in .venv"
  "$PY" -m venv .venv
fi
VPY=".venv/bin/python"

echo "== Installing Python packages"
"$VPY" -m pip install --upgrade pip --quiet
"$VPY" -m pip install -r requirements.txt --quiet

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "== Created .env from .env.example (edit it before building the database)"
fi

bash scripts/regenerate_all.sh

if command -v npm >/dev/null 2>&1; then
  echo "== Installing dashboard packages (frontend/)"
  (cd frontend && npm install --no-fund --no-audit)
else
  echo "== npm not found - skipping dashboard install (install Node.js 22 LTS to run the React app)"
fi

echo "== Running tests"
"$VPY" -m pytest tests -q

cat <<'EOF'

Setup complete.
  Activate the environment:  source .venv/bin/activate
  In VS Code: Ctrl/Cmd+Shift+P -> "Python: Select Interpreter" -> .venv
  Next: build the database  ->  bash database/build_database.sh
        start the app        ->  bash scripts/start_api.sh   and   bash scripts/start_dashboard.sh
EOF
