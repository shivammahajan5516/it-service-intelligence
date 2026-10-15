# Rebuild every analysis output from the database (Windows). Requires database\build_database.ps1 first.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$Py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
foreach ($s in @("scripts\reconcile_db.py", "scripts\run_sql_analysis.py", "analytics\run_analysis.py",
                 "analytics\model.py", "powerbi\expected_values.py", "scripts\generate_api_docs.py")) {
    Write-Host "== $s"
    if ($s -eq "scripts\run_sql_analysis.py") { & $Py $s --strict } else { & $Py $s }
    if ($LASTEXITCODE -ne 0) { throw "$s failed" }
}
Write-Host "All analysis outputs regenerated."
