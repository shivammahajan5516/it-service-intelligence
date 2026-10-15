# Regenerate every dataset file, validate it and prove reproducibility (Windows PowerShell).
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\regenerate_all.ps1 [-Seed 42]
param([int]$Seed = 42)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$Py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

function Run($argsList) {
    & $Py @argsList
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $($argsList -join ' ')" }
}

Write-Host "== 1/3 Generating synthetic dataset (seed=$Seed) with $Py"
Run @("scripts\generate_dataset.py", "--seed", "$Seed")

Write-Host "== 2/3 Validating"
Run @("scripts\validate_dataset.py")

Write-Host "== 3/3 Checking reproducibility"
Run @("scripts\check_reproducibility.py")

Write-Host "Done. Reports in data\reports\"
