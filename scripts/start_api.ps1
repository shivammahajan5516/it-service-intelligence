# Start the FastAPI backend on http://localhost:8000 (docs at /docs). Windows PowerShell.
#   powershell -ExecutionPolicy Bypass -File scripts\start_api.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$Py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
$Port = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
& $Py -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port $Port
