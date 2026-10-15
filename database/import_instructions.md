# Importing the CSV files into PostgreSQL

The fastest route is the one-command build in section 1. Section 3 explains what each step does
and how to run the steps by hand, which is useful in interviews or when debugging.

## 1. One-command build (recommended)

**Prerequisites:** PostgreSQL 16 (15+ works) is installed and running, `psql` is available, and you
have run the Phase 2 data setup so `data/raw/` exists.

1. Create `.env` from the template (the setup script does this for you) and fill in:

   ```ini
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=it_service_intelligence
   DB_ADMIN_USER=postgres              # Windows installer default; blank on macOS Homebrew
   DB_ADMIN_PASSWORD=<your postgres password>
   DB_APP_USER=itsi_app                # read-only role the build creates
   DB_APP_PASSWORD=<choose one>
   ```

2. Run the build **from the project root**:

   | Platform | Command |
   |---|---|
   | Windows (PowerShell) | `powershell -ExecutionPolicy Bypass -File database\build_database.ps1` |
   | macOS / Linux / WSL | `bash database/build_database.sh` |
   | VS Code | `Ctrl+Shift+P` → **Tasks: Run Task** → **Database: build** |

   The build takes about 5 seconds and ends with 15 `PASS` checks.

3. Verify and run the analysis:

   ```bash
   python scripts/reconcile_db.py        # 82 KPI comparisons vs an independent pandas implementation
   python scripts/run_sql_analysis.py    # runs all 37 queries -> docs/sql_analysis.md
   ```

## 2. Pipeline

```
data/raw/*.csv ──\copy──▶ staging.*  ──transform_clean.sql──▶ clean.*  ──analytics_views.sql──▶ analytics.*
 (as exported)          (all TEXT,            (typed, standardised,            (KPI populations,
                         nothing rejected)      flagged, de-duplicated,          fact + dims + KPI views)
                                                constraints.sql + indexes.sql)
                                    every correction ──▶ audit.dq_issues
```

| Order | File | Purpose |
|---|---|---|
| 1 | `setup_roles.sql` | Creates the database and the read-only role `itsi_app` (run against `postgres`) |
| 2 | `schema.sql` | Drops and recreates the `staging`, `clean`, `analytics` and `audit` schemas; safe-cast helper functions; all tables |
| 3 | `load_staging.sql` | `\copy` each CSV into `staging` and log row counts |
| 4 | `transform_clean.sql` | Applies the business rules: types, label mapping, de-duplication, DQ flags and an audit entry for every change |
| 5 | `constraints.sql` | 44 primary-key, foreign-key, unique and check constraints on `clean` |
| 6 | `indexes.sql` | Indexes on the API filter columns, foreign keys, the repeat-incident window, and partial indexes |
| 7 | `analytics_views.sql` | The `fact_tickets` materialised view, dimension views and KPI views |
| 8 | `grants.sql` | `itsi_app` gets `SELECT` on `analytics` only |
| 9 | `checks.sql` | 15 reconciliation and integrity assertions; raises an error if any fails |

## 3. Running the steps manually

From the project root, with the admin connection settings exported (`PGHOST`, `PGUSER`, `PGPASSWORD`):

```bash
psql -d postgres -v db_name=it_service_intelligence -v app_user=itsi_app \
     -v app_password='your-password' -f database/setup_roles.sql

psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/schema.sql
psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/load_staging.sql
psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/transform_clean.sql
psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/constraints.sql
psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/indexes.sql
psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/analytics_views.sql
psql -v ON_ERROR_STOP=1 -d it_service_intelligence -v app_user=itsi_app -f database/grants.sql
psql -v ON_ERROR_STOP=1 -d it_service_intelligence -f database/checks.sql
```

### Why `\copy` and not `COPY`?

`COPY ... FROM 'file'` runs **on the database server** and needs superuser rights or the
`pg_read_server_files` role, plus a path the server can see. `\copy` is a `psql` command that
reads the file **on your machine** and streams it to the server. It works for a local database,
Docker, or a cloud database (Azure, AWS RDS, Supabase) without copying files onto the server.

### Loading with a GUI instead (pgAdmin / DBeaver)

1. Run `schema.sql` in the query tool.
2. Right-click each `staging.<table>` → **Import/Export Data** → **Import** → choose the CSV.
   Set Format = csv, Header = on, Delimiter = `,` and NULL string = empty.
3. Run the remaining files, from `transform_clean.sql` to `checks.sql`, in order.

## 4. Re-loading after regenerating the data

The build is idempotent. After `scripts/regenerate_all.sh`, run the build again: it drops and
recreates the schemas. If you load new rows into `clean` by another route, refresh the fact:

```sql
REFRESH MATERIALIZED VIEW analytics.fact_tickets;
```

## 5. Connecting tools

| Tool | Settings |
|---|---|
| VS Code SQLTools | Driver PostgreSQL; host and port from `.env`; database `it_service_intelligence`; user `itsi_app` (read-only) |
| pgAdmin / DBeaver | Same settings. Use the admin user only to run the build |
| Power BI (Phase 8) | Get Data → PostgreSQL database → server `localhost:5432`, database `it_service_intelligence`, user `itsi_app`. Import the `analytics` views |
| FastAPI (Phase 7) | Reads `DB_*` from `.env` as `itsi_app` |

## 6. Troubleshooting

| Error | Cause / fix |
|---|---|
| `psql: command not found` / not recognised | Add PostgreSQL's `bin` folder to PATH (see `docs/SETUP.md`). The Windows script also searches `C:\Program Files\PostgreSQL\*\bin` automatically |
| `password authentication failed for user "postgres"` | `DB_ADMIN_PASSWORD` in `.env` doesn't match the password you set during installation |
| `could not open file "data/raw/tickets.csv"` | The build was run from the wrong folder. Run it from the project root, or use the build script, which changes to the right folder itself |
| `role "itsi_app" does not exist` (running a step by hand) | Run `setup_roles.sql` first |
| `permission denied for schema clean` as `itsi_app` | This is expected: the app role can only read `analytics` (least privilege) |
| `database "it_service_intelligence" is being accessed by other users` | Close pgAdmin, DBeaver or SQLTools connections, then rebuild |
| A `checks.sql` check reports `FAIL` | The data or a transform changed. Read the `expected` and `actual` columns, then rerun `scripts/validate_dataset.py` |
