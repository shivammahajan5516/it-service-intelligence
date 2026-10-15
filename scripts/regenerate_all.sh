#!/usr/bin/env bash
# Regenerate every dataset file, validate it and prove reproducibility.
# Usage: bash scripts/regenerate_all.sh [seed]
set -euo pipefail
cd "$(dirname "$0")/.."
SEED="${1:-42}"

# Prefer the project virtual environment if it exists
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="${PYTHON:-python3}"; fi

echo "== 1/3 Generating synthetic dataset (seed=${SEED}) with ${PY}"
"$PY" scripts/generate_dataset.py --seed "${SEED}"

echo "== 2/3 Validating"
"$PY" scripts/validate_dataset.py

echo "== 3/3 Checking reproducibility"
"$PY" scripts/check_reproducibility.py

echo "Done. Reports in data/reports/"
