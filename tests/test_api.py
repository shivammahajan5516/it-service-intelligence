"""
HTTP-level API tests using FastAPI's TestClient.

Requires: pip install -r requirements.txt  (fastapi, httpx, psycopg) and a built database.
Skipped automatically when FastAPI is not installed or the database is unreachable.

    pytest tests/test_api.py -q
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import psql_runner  # noqa: E402
from backend.app import main  # noqa: E402

try:  # prefer the real driver; fall back to psql so the HTTP layer is still exercised
    import psycopg  # noqa: F401
    RUNNER = None
except ImportError:
    RUNNER = psql_runner.run

if not psql_runner.available():
    pytest.skip("database not reachable", allow_module_level=True)

if RUNNER is not None:
    main.app.dependency_overrides[main.get_runner] = lambda: RUNNER

client = TestClient(main.app, raise_server_exceptions=False)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"
    assert "x-request-id" in r.headers


def test_meta_lists_filters():
    r = client.get("/api/meta")
    body = r.json()
    assert r.status_code == 200 and len(body["teams"]) == 8 and body["synthetic_data"] is True


@pytest.mark.parametrize("path", ["/api/overview", "/api/trends", "/api/sla-performance",
                                  "/api/root-causes", "/api/team-performance", "/api/customer-analysis",
                                  "/api/tickets", "/api/data-quality"])
def test_every_endpoint_returns_200(path):
    r = client.get(path, params={"start_date": "2025-07-01", "end_date": "2025-12-31"}
                   if path != "/api/data-quality" else None)
    assert r.status_code == 200, r.text


def test_overview_filters_and_previous_period():
    r = client.get("/api/overview", params={"start_date": "2025-07-01", "end_date": "2025-12-31",
                                            "priority": ["P1", "P2"], "team": "T03"})
    body = r.json()
    assert r.status_code == 200
    assert body["filters"]["priority"] == ["P1", "P2"] and body["filters"]["team"] == ["T03"]
    assert body["previous"]["total_tickets"] > 0


@pytest.mark.parametrize("params", [
    {"start_date": "2025-31-01"}, {"start_date": "2025-06-01", "end_date": "2025-01-01"},
    {"priority": "P7"}, {"team": "T1"}, {"category": "Not A Category"}, {"region": "Atlantis"},
])
def test_invalid_filters_return_422(params):
    r = client.get("/api/overview", params=params)
    assert r.status_code == 422, r.text
    assert "detail" in r.json()


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 101}, {"sort": "password"},
                                    {"order": "sideways"}, {"status": "lost"}])
def test_invalid_paging_returns_422(params):
    assert client.get("/api/tickets", params=params).status_code == 422


def test_tickets_pagination_is_consistent():
    a = client.get("/api/tickets", params={"page": 1, "page_size": 20}).json()
    b = client.get("/api/tickets", params={"page": 2, "page_size": 20}).json()
    assert a["total"] == b["total"] and len(a["items"]) == 20
    assert not {t["ticket_id"] for t in a["items"]} & {t["ticket_id"] for t in b["items"]}


def test_cors_allows_dashboard_origin():
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_unknown_route_is_404():
    assert client.get("/api/nope").status_code == 404
