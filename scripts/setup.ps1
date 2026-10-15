# One-time setup for Windows (PowerShell).
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# Creates .venv, installs Python dependencies, builds and validates the dataset, runs tests.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# Find Python: prefer the "py" launcher installed by python.org, then "python"
$PyExe = $null; $PyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $PyExe = "py"; $PyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $PyExe = "python" }
if (-not $PyExe) { throw "Python not found. Install Python 3.11+ from python.org and tick 'Add python.exe to PATH' (see docs\SETUP.md)." }

$ver = & $PyExe @PyArgs -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$ver -lt [version]"3.11") { throw "Python 3.11+ required, found $ver" }
Write-Host "Python $ver OK"

if (-not (Test-Path ".venv")) {
    Write-Host "== Creating virtual environment in .venv"
    & $PyExe @PyArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
}
$VPy = ".venv\Scripts\python.exe"

Write-Host "== Installing Python packages"
& $VPy -m pip install --upgrade pip --quiet
& $VPy -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

if ((-not (Test-Path ".env")) -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "== Created .env from .env.example (edit it before building the database)"
}

& powershell -ExecutionPolicy Bypass -File scripts\regenerate_all.ps1
if ($LASTEXITCODE -ne 0) { throw "Data build failed" }

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "== Installing dashboard packages (frontend\)"
    Push-Location frontend
    npm install --no-fund --no-audit
    $npmExit = $LASTEXITCODE
    Pop-Location
    if ($npmExit -ne 0) { throw "npm install failed" }
} else {
    Write-Host "== npm not found - skipping dashboard install (install Node.js 22 LTS to run the React app)"
}

Write-Host "== Running tests"
& $VPy -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }

Write-Host ""
Write-Host "Setup complete."
Write-Host "  Activate the environment:  .\.venv\Scripts\Activate.ps1"
Write-Host "  In VS Code: Ctrl+Shift+P -> 'Python: Select Interpreter' -> .venv"
Write-Host "  Next: build the database -> powershell -ExecutionPolicy Bypass -File database\build_database.ps1"
Write-Host "        start the app      -> scripts\start_api.ps1  and  scripts\start_dashboard.ps1"
