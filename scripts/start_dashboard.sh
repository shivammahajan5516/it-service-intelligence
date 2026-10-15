#!/usr/bin/env bash
# Start the React dashboard on http://localhost:5173 (installs npm packages on first run).
set -euo pipefail
cd "$(dirname "$0")/../frontend"
command -v npm >/dev/null || { echo "ERROR: npm not found - install Node.js 22 LTS (docs/SETUP.md)"; exit 1; }
[ -d node_modules ] || npm install
exec npm run dev
