# Start the React dashboard on http://localhost:5173 (installs npm packages on first run). Windows.
#   powershell -ExecutionPolicy Bypass -File scripts\start_dashboard.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\frontend")
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm not found - install Node.js 22 LTS (docs\SETUP.md)" }
if (-not (Test-Path "node_modules")) { npm install; if ($LASTEXITCODE -ne 0) { throw "npm install failed" } }
npm run dev
