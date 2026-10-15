#!/usr/bin/env python3
"""
Build docs/api_reference.md with REAL example responses.

Runs each endpoint's service function (the same code FastAPI calls) against the
database via tests/psql_runner.py, then trims long lists for readability.
    python scripts/generate_api_docs.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from backend.app import services  # noqa: E402
from backend.app.filters import Filters, build_page  # noqa: E402
from datetime import date  # noqa: E402
import psql_runner  # noqa: E402

run = psql_runner.run
H2 = Filters(date(2025, 7, 1), date(2025, 12, 31))


def trim(obj, n=3):
    if isinstance(obj, list):
        return [trim(x, n) for x in obj[:n]] + (["... (%d more)" % (len(obj) - n)] if len(obj) > n else [])
    if isinstance(obj, dict):
        return {k: trim(v, n) for k, v in obj.items()}
    return obj


ENDPOINTS = [
    ("GET /api/health", "Liveness + database check. 200 when the database answers, 503 otherwise.",
     "", lambda: services.health(run)),
    ("GET /api/meta", "Filter options (teams, categories, regions) and the data range. Cached per process.",
     "", lambda: services.meta(run)),
    ("GET /api/overview", "Headline KPIs for the filtered period, the same KPIs for the equal-length previous "
     "period, the difference, and the monthly series.", "?start_date=2025-07-01&end_date=2025-12-31",
     lambda: services.overview(run, H2)),
    ("GET /api/trends", "Monthly KPI series.", "?start_date=2025-07-01&end_date=2025-12-31&team=T03",
     lambda: services.trends(run, Filters(H2.start, H2.end, teams=("T03",)))),
    ("GET /api/sla-performance", "Compliance by priority / category / team / region, resolution-time "
     "distribution, first response by channel, monthly breach trend per priority.",
     "?start_date=2025-07-01&end_date=2025-12-31", lambda: services.sla_performance(run, H2)),
    ("GET /api/root-causes", "Pareto of incident root causes, root cause x priority matrix, repeat incidents, "
     "escalation analysis, slowest subcategories.", "?start_date=2025-07-01&end_date=2025-12-31",
     lambda: services.root_causes(run, H2)),
    ("GET /api/team-performance", "Team scorecard and monthly workload per team.",
     "?start_date=2025-07-01&end_date=2025-12-31", lambda: services.team_performance(run, H2)),
    ("GET /api/customer-analysis", "Paginated, searchable, sortable customer table plus highlight lists. "
     "Extra params: `page`, `page_size` (1-100), `sort` (" + ", ".join(services.CUSTOMER_SORTS) + "), "
     "`order` (asc/desc), `search`, `min_tickets`.",
     "?start_date=2025-07-01&end_date=2025-12-31&sort=sla_breach_pct&min_tickets=10&page_size=3",
     lambda: services.customer_analysis(run, H2, build_page(1, 3, "sla_breach_pct", "desc", "",
                                                            tuple(services.CUSTOMER_SORTS), "tickets"), 10)),
    ("GET /api/tickets", "Paginated ticket list. Extra params: `page`, `page_size`, `sort` ("
     + ", ".join(services.TICKET_SORTS) + "), `order`, `search` (ticket id or customer name), `status` ("
     + ", ".join(services.TICKET_STATUS) + ").", "?status=open&priority=P1&page_size=2",
     lambda: services.tickets(run, Filters(priorities=("P1",)),
                              build_page(1, 2, "created_at", "desc", "", tuple(services.TICKET_SORTS), "created_at"),
                              "open")),
    ("GET /api/data-quality", "Data-quality rules applied by the pipeline and the records affected.", "",
     lambda: services.data_quality(run)),
]


def main():
    L = ["# API reference", "",
         "FastAPI service in `backend/`. Interactive docs when running: <http://localhost:8000/docs> "
         "(Swagger) and `/redoc`. **All data is synthetic.**", "",
         "## Conventions", "",
         "- **Base URL:** `http://localhost:8000`. All endpoints are `GET` and read-only.",
         "- **Common filters** (every dashboard endpoint): `start_date`, `end_date` (YYYY-MM-DD, inclusive), "
         "`priority` (P1-P4), `team` (T01-T08), `category`, `region`. Lists can be repeated "
         "(`?team=T01&team=T03`) or comma-separated (`?team=T01,T03`).",
         "- **Validation:** invalid input returns **422** with `{\"detail\": \"...\"}` (unknown priority, bad date, "
         "start after end, unknown category/region, page_size > 100, sort column not allowed).",
         "- **Errors:** database problems return **503** with a generic message (details are logged server-side "
         "only). Unknown routes return 404.",
         "- **Security:** parameterised SQL only; sort columns from a whitelist; the API connects as the "
         "read-only role `itsi_app` in read-only transactions with a statement timeout; credentials from "
         "environment variables; CORS restricted to `API_CORS_ORIGINS`.",
         "- **Previous period** = the same number of days immediately before `start_date` "
         "(e.g. 2025-07-01..2025-12-31, 184 days -> 2024-12-29..2025-06-30).",
         "- **Every response** includes an `x-request-id` header; each request is logged with method, path, "
         "status and duration.", "",
         "Examples below are real responses from the seed-42 database (long lists trimmed to 3 items).", ""]
    for title, desc, qs, fn in ENDPOINTS:
        body = json.dumps(trim(fn()), indent=2, default=str)
        L += [f"## `{title}`", "", desc, "", f"Example: `{title.split()[1]}{qs}`", "", "```json", body, "```", ""]
    (ROOT / "docs" / "api_reference.md").write_text("\n".join(L))
    print("docs/api_reference.md written")


if __name__ == "__main__":
    main()
