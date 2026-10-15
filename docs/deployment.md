# Deployment

The project is designed to run **locally** as a portfolio piece. This page explains how to run a
production-style build locally, and what would have to change before sharing it beyond your own
machine.

## 1. Local production-style run

```bash
# 1. Database (once, or after regenerating data)
bash database/build_database.sh                 # Windows: database\build_database.ps1

# 2. API with multiple workers (no auto-reload)
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 2

# 3. Dashboard as static files
cd frontend && npm ci && npm run build && npm run preview     # serves dist/ on http://localhost:5173
```

Set `VITE_API_BASE_URL` in `.env` **before** `npm run build`, because the value is compiled into the
bundle.

## 2. Hosting options (if you want a public demo)

| Layer | Option | Notes |
|---|---|---|
| Database | Neon, Supabase or Azure Database for PostgreSQL (free or low tiers) | Run `setup_roles.sql` and the build against the cloud host; `\copy` streams the CSVs from your machine. Set `DB_HOST` and enable SSL (`sslmode=require` in the connection) |
| API | Render, Railway, Fly.io or Azure App Service | Start command `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`; set every `DB_*` variable and `API_CORS_ORIGINS=https://<your-dashboard-domain>` in the platform's secret settings |
| Dashboard | Netlify, Vercel, GitHub Pages or Azure Static Web Apps | Build command `npm run build`, output folder `frontend/dist`, environment variable `VITE_API_BASE_URL=https://<your-api>`. Add an SPA fallback so `/*` → `index.html` (React Router) |
| Power BI | Power BI Service | Publish from Desktop; an on-premises data gateway is needed for a local database |

Because the data is synthetic and the API is read-only, a public demo carries little risk. Even so,
apply section 3 before sharing the link.

## 3. Hardening checklist before sharing

- [ ] **Authentication.** Put the dashboard and API behind sign-in (Azure AD / Entra ID, Auth0,
      Cloudflare Access) and add role-based access (NFR-13).
- [ ] **CORS.** `API_CORS_ORIGINS` should list only the dashboard's real origin.
- [ ] **TLS everywhere.** Use HTTPS for the API and `sslmode=require` for the database.
- [ ] **Secrets in the platform's secret store,** never in the repository. `.env` stays git-ignored.
- [ ] **Read-only database role** `itsi_app`, already enforced by grants and read-only sessions.
- [ ] **Rate limiting** at the proxy or platform. Queries already have a statement timeout (5 s).
- [ ] **Monitoring.** Ship the API access logs (each request has an `x-request-id`); alert on 5xx
      responses and on `/api/health` failing.
- [ ] **Refresh job.** Schedule the database build (cron or GitHub Actions) if the data changes.

## 4. Continuous integration (suggested)

A GitHub Actions workflow could:
1. Start a `postgres:16` service container.
2. Run `pip install -r requirements.txt`.
3. Run `bash scripts/regenerate_all.sh` and `bash database/build_database.sh`, with `DB_*` variables
   from repository secrets.
4. Run `pytest tests -q`.
5. Run `cd frontend && npm ci && npm run build`.

This catches any change that breaks reproducibility, the KPI reconciliation, or the type check.
