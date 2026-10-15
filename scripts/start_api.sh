#!/usr/bin/env bash
# Start the FastAPI backend on http://localhost:8000 (docs at /docs). macOS / Linux / WSL.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="${PYTHON:-python3}"; fi
exec "$PY" -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port "${API_PORT:-8000}"
