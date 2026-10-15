# Build the whole PostgreSQL layer from the CSVs in data\raw\ (Windows PowerShell).
#   powershell -ExecutionPolicy Bypass -File database\build_database.ps1
# Reads connection settings from .env (see .env.example). Re-runnable.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# ---- load .env ----
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2]
        }
    }
}
function Get-Setting($name, $default) {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrEmpty($v)) { return $default } else { return $v }
}
$DbHost = Get-Setting "DB_HOST" "localhost"
$DbPort = Get-Setting "DB_PORT" "5432"
$DbName = Get-Setting "DB_NAME" "it_service_intelligence"
$AppUser = Get-Setting "DB_APP_USER" "itsi_app"
$AppPassword = Get-Setting "DB_APP_PASSWORD" ""
if ([string]::IsNullOrEmpty($AppPassword)) { throw "Set DB_APP_PASSWORD in .env" }

# ---- find psql (PATH first, then the default installer location) ----
$Psql = (Get-Command psql -ErrorAction SilentlyContinue).Source
if (-not $Psql) {
    $Psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $Psql) { throw "psql not found - install PostgreSQL 16 (docs\SETUP.md)" }

$env:PGHOST = $DbHost; $env:PGPORT = $DbPort
$admin = Get-Setting "DB_ADMIN_USER" ""
$adminPw = Get-Setting "DB_ADMIN_PASSWORD" ""
if ($admin) { $env:PGUSER = $admin }
if ($adminPw) { $env:PGPASSWORD = $adminPw }
$env:PGCLIENTENCODING = "UTF8"

function Run-Psql([string[]]$a) {
    & $Psql -X -q -v ON_ERROR_STOP=1 @a
    if ($LASTEXITCODE -ne 0) { throw "psql failed: $($a -join ' ')" }
}

Write-Host "== 1/11 Database and read-only role"
Run-Psql @("-d", "postgres", "-v", "db_name=$DbName", "-v", "app_user=$AppUser",
           "-v", "app_password=$AppPassword", "-f", "database/setup_roles.sql")

$step = 2
foreach ($f in @("schema", "load_staging", "transform_clean", "constraints", "indexes", "analytics_views", "powerbi_views")) {
    Write-Host "== $step/11 $f.sql"
    Run-Psql @("-d", $DbName, "-f", "database/$f.sql") | Out-Null
    $step++
}

Write-Host "== 9/11 grants.sql"
Run-Psql @("-d", $DbName, "-v", "app_user=$AppUser", "-f", "database/grants.sql") | Out-Null

Write-Host "== 10/11 checks.sql"
& $Psql -X -v ON_ERROR_STOP=1 -d $DbName -f "database/checks.sql"
if ($LASTEXITCODE -ne 0) { throw "Database checks failed" }

Write-Host "== 11/11 export_analytics.sql -> data\processed\"
New-Item -ItemType Directory -Force -Path "data\processed" | Out-Null
Run-Psql @("-d", $DbName, "-f", "database/export_analytics.sql")

Write-Host "Database '$DbName' built. API/Power BI user: $AppUser (read-only, analytics schema)."
