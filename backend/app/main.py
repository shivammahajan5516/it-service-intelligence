"""
IT Service Intelligence Platform - REST API (FastAPI).

Run (from the project root, with .env filled in and the database built):
    uvicorn backend.app.main:app --reload --port 8000
Docs: http://localhost:8000/docs (Swagger UI) and /redoc
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Callable

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import services
from .config import settings
from .filters import Filters, FilterError, Page, build_filters, build_page

logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("itsi.api")


def get_runner() -> Callable:
    """Dependency returning the query executor (overridable in tests)."""
    from . import db
    return db.run


_META_CACHE: dict = {}


def allowed_values(run: Callable = Depends(get_runner)) -> dict:
    if not _META_CACHE:
        _META_CACHE.update(services.meta(run))
    return _META_CACHE


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from . import db
        db.open_pool()
    except Exception:  # noqa: BLE001 - the API still starts; /api/health will report the problem
        log.exception("Could not open database pool at startup")
    yield
    try:
        from . import db
        db.close_pool()
    except Exception:  # noqa: BLE001
        pass


app = FastAPI(
    title="IT Service Intelligence API",
    version="1.0.0",
    description=("Read-only analytics API for SLA monitoring, root-cause analysis and operational "
                 "performance. **All data is synthetic** (fictional Northbridge Managed Services Ltd). "
                 "KPI definitions: docs/04_kpi_catalogue.md; population rules: docs/05_business_rules.md."),
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False,
                   allow_methods=["GET"], allow_headers=["*"])


@app.middleware("http")
async def access_log(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    response.headers["x-request-id"] = rid
    log.info("%s %s %s %d %.1fms", rid, request.method, request.url.path, response.status_code, ms)
    return response


@app.exception_handler(FilterError)
async def filter_error(_: Request, exc: FilterError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # Database / driver errors: log details server-side, return a generic 503 to the client
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=503, content={"detail": "The analytics database is unavailable or "
                                                            "returned an error. Please try again."})


# ------------------------------------------------------------------ dependencies
ListParam = Annotated[list[str] | None, Query()]


def filters_dep(
    start_date: Annotated[str | None, Query(description="YYYY-MM-DD (inclusive)")] = None,
    end_date: Annotated[str | None, Query(description="YYYY-MM-DD (inclusive)")] = None,
    priority: Annotated[list[str] | None, Query(description="P1-P4; repeat or comma-separate")] = None,
    team: Annotated[list[str] | None, Query(description="Team id, e.g. T03")] = None,
    category: ListParam = None,
    region: ListParam = None,
    allowed: dict = Depends(allowed_values),
) -> Filters:
    return build_filters(start_date, end_date, priority, team, category, region,
                         allowed_categories=set(allowed["categories"]), allowed_regions=set(allowed["regions"]))


# ------------------------------------------------------------------ endpoints
@app.get("/api/health", tags=["system"], summary="Liveness and database connectivity")
def health(run: Callable = Depends(get_runner)):
    try:
        return services.health(run)
    except Exception as exc:  # noqa: BLE001
        log.warning("Health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@app.get("/api/meta", tags=["system"], summary="Filter options and data range")
def meta(allowed: dict = Depends(allowed_values)):
    return allowed


@app.get("/api/overview", tags=["dashboard"], summary="Headline KPIs vs previous period + monthly trend")
def overview(f: Filters = Depends(filters_dep), run: Callable = Depends(get_runner)):
    return services.overview(run, f)


@app.get("/api/trends", tags=["dashboard"], summary="Monthly KPI trend")
def trends(f: Filters = Depends(filters_dep), run: Callable = Depends(get_runner)):
    return services.trends(run, f)


@app.get("/api/sla-performance", tags=["dashboard"], summary="SLA compliance by priority, category, team")
def sla_performance(f: Filters = Depends(filters_dep), run: Callable = Depends(get_runner)):
    return services.sla_performance(run, f)


@app.get("/api/root-causes", tags=["dashboard"], summary="Pareto, root-cause matrix, repeats, escalation")
def root_causes(f: Filters = Depends(filters_dep), run: Callable = Depends(get_runner)):
    return services.root_causes(run, f)


@app.get("/api/team-performance", tags=["dashboard"], summary="Team scorecard and monthly workload")
def team_performance(f: Filters = Depends(filters_dep), run: Callable = Depends(get_runner)):
    return services.team_performance(run, f)


@app.get("/api/customer-analysis", tags=["dashboard"], summary="Searchable, sortable customer table")
def customer_analysis(
    f: Filters = Depends(filters_dep),
    page: int = 1, page_size: int = 25, sort: str = "tickets", order: str = "desc", search: str = "",
    min_tickets: Annotated[int, Query(ge=1, le=10000)] = 1,
    run: Callable = Depends(get_runner),
):
    pg = build_page(page, page_size, sort, order, search, tuple(services.CUSTOMER_SORTS), "tickets")
    return services.customer_analysis(run, f, pg, min_tickets)


@app.get("/api/tickets", tags=["dashboard"], summary="Paginated ticket list for drill-down")
def tickets(
    f: Filters = Depends(filters_dep),
    page: int = 1, page_size: int = 25, sort: str = "created_at", order: str = "desc", search: str = "",
    status: str | None = None,
    run: Callable = Depends(get_runner),
):
    pg = build_page(page, page_size, sort, order, search, tuple(services.TICKET_SORTS), "created_at")
    if status is not None and status not in services.TICKET_STATUS:
        raise FilterError(f"status must be one of: {', '.join(services.TICKET_STATUS)}")
    return services.tickets(run, f, pg, status)


@app.get("/api/data-quality", tags=["system"], summary="Data-quality rules applied by the pipeline")
def data_quality(run: Callable = Depends(get_runner)):
    return services.data_quality(run)
