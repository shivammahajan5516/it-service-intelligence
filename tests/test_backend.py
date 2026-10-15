"""
Backend tests (Phase 7).

Part 1 - filter validation and SQL building: pure Python, always runs.
Part 2 - every endpoint's SQL executed against the real database through
         tests/psql_runner.py; checks results reconcile with the KPI views.
         Skipped if the database is not reachable.
API-level (FastAPI TestClient) tests are in tests/test_api.py.

    pytest tests/test_backend.py -q      (or: python tests/test_backend.py)
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from backend.app import services  # noqa: E402
from backend.app.filters import FilterError, Filters, build_filters, build_page, like_pattern, where_clause  # noqa: E402
import psql_runner  # noqa: E402


class Skip(Exception):
    pass


def need_db():
    if not psql_runner.available():
        try:
            import pytest
            pytest.skip("database not reachable")
        except ImportError:
            raise Skip("database not reachable")


def raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except FilterError:
        return True
    return False


# ------------------------------------------------------------------ part 1: validation
def test_filters_parse_lists_and_dates():
    f = build_filters("2025-01-01", "2025-03-31", ["p1,P2"], "T01,T03", None, ["London"])
    assert f.start == date(2025, 1, 1) and f.priorities == ("P1", "P2") and f.teams == ("T01", "T03")
    assert f.regions == ("London",)


def test_filters_reject_bad_input():
    assert raises(build_filters, "2025-13-01")
    assert raises(build_filters, "2025-02-01", "2025-01-01")
    assert raises(build_filters, priority="P9")
    assert raises(build_filters, team="T01; DROP TABLE x")
    assert raises(build_filters, category="Nope", allowed_categories={"Network"})
    assert raises(build_filters, region="x" * 65)


def test_where_clause_is_parameterised():
    f = build_filters("2025-01-01", "2025-01-31", "P1", "T03", "Network", "London")
    sql, params = where_clause(f)
    assert "Network" not in sql and "London" not in sql and "T03" not in sql
    assert params["end_excl"] == date(2025, 2, 1)          # inclusive end date
    assert params["priorities"] == ["P1"]


def test_previous_period_same_length():
    prev = Filters(date(2025, 7, 1), date(2025, 12, 31)).previous_period()   # 184 days -> 184 days before
    assert prev.start == date(2024, 12, 29) and prev.end == date(2025, 6, 30)
    assert (prev.end - prev.start) == (date(2025, 12, 31) - date(2025, 7, 1))


def test_page_validation_and_like_escape():
    assert raises(build_page, page=0, allowed_sorts=("a",), default_sort="a")
    assert raises(build_page, page_size=500, allowed_sorts=("a",), default_sort="a")
    assert raises(build_page, sort="tickets; drop", allowed_sorts=("tickets",))
    assert raises(build_page, order="sideways", allowed_sorts=("a",), default_sort="a")
    assert like_pattern("50%_off") == "%50\\%\\_off%"


# ------------------------------------------------------------------ part 2: SQL against the DB
def kpi_overall():
    return psql_runner.run({"k": ("SELECT * FROM analytics.kpi_overall", {})})["k"][0]


def test_overview_unfiltered_matches_kpi_view():
    need_db()
    o = services.overview(psql_runner.run, Filters())
    k = kpi_overall()
    assert o["current"]["total_tickets"] == k["total_tickets"]
    assert abs(o["current"]["sla_breach_pct"] - k["sla_breach_pct"]) < 0.01
    assert abs(o["current"]["median_resolution_hours"] - k["median_resolution_hours"]) < 0.01
    assert sum(m["tickets"] for m in o["monthly"]) == k["total_tickets"]
    assert o["previous"] is None                       # no dates -> no previous period


def test_overview_previous_period_and_change():
    need_db()
    o = services.overview(psql_runner.run, Filters(date(2025, 7, 1), date(2025, 12, 31)))
    assert o["previous"]["total_tickets"] > 0
    assert o["previous_period"] == {"start_date": "2024-12-29", "end_date": "2025-06-30"}
    assert abs(o["change"]["sla_breach_pct"]
               - (o["current"]["sla_breach_pct"] - o["previous"]["sla_breach_pct"])) < 0.011


def test_filters_partition_the_data():
    need_db()
    total = services.overview(psql_runner.run, Filters())["current"]["total_tickets"]
    parts = sum(services.overview(psql_runner.run, Filters(priorities=(p,)))["current"]["total_tickets"]
                for p in ("P1", "P2", "P3", "P4"))
    assert parts == total


def test_sla_performance_shapes():
    need_db()
    s = services.sla_performance(psql_runner.run, Filters(teams=("T03",)))
    assert [r["priority"] for r in s["by_priority"]] == ["P1", "P2", "P3", "P4"]
    assert [t["team_id"] for t in s["by_team"]] == ["T03"]
    assert all(set(b) >= {"bucket", "P1", "P2", "P3", "P4"} for b in s["resolution_distribution"])
    assert len(s["breach_trend"]) == 24


def test_root_cause_pareto_ends_at_100():
    need_db()
    r = services.root_causes(psql_runner.run, Filters())
    assert r["pareto"][-1]["cumulative_pct"] == 100.0
    assert r["pareto"][0]["incidents"] >= r["pareto"][-1]["incidents"]
    assert 0 < r["repeat_summary"]["repeat_incident_pct"] < 100


def test_team_performance_sums_to_total():
    need_db()
    t = services.team_performance(psql_runner.run, Filters())
    assert len(t["teams"]) == 8
    assert sum(x["tickets"] for x in t["teams"]) == kpi_overall()["total_tickets"]


def test_customer_analysis_pagination_search_sort():
    need_db()
    pg = build_page(1, 10, "tickets", "desc", "", tuple(services.CUSTOMER_SORTS), "tickets")
    c = services.customer_analysis(psql_runner.run, Filters(), pg)
    assert len(c["items"]) == 10 and c["total"] >= 400
    vols = [i["tickets"] for i in c["items"]]
    assert vols == sorted(vols, reverse=True)
    pg2 = build_page(2, 10, "tickets", "desc", "", tuple(services.CUSTOMER_SORTS), "tickets")
    c2 = services.customer_analysis(psql_runner.run, Filters(), pg2)
    assert not {i["customer_id"] for i in c["items"]} & {i["customer_id"] for i in c2["items"]}
    name = c["items"][0]["customer_name"]
    s = services.customer_analysis(psql_runner.run, Filters(),
                                   build_page(1, 10, "tickets", "desc", name[:8], tuple(services.CUSTOMER_SORTS), "tickets"))
    assert any(i["customer_name"] == name for i in s["items"])


def test_search_input_cannot_inject_sql():
    need_db()
    evil = "x'; DROP TABLE analytics.fact_tickets; --"
    pg = build_page(1, 5, "created_at", "desc", evil, tuple(services.TICKET_SORTS), "created_at")
    r = services.tickets(psql_runner.run, Filters(), pg)
    assert r["total"] == 0
    assert kpi_overall()["total_tickets"] > 0             # table still there


def test_tickets_status_filter_and_paging():
    need_db()
    pg = build_page(1, 25, "created_at", "desc", "", tuple(services.TICKET_SORTS), "created_at")
    r = services.tickets(psql_runner.run, Filters(), pg, status="open")
    assert r["total"] == kpi_overall()["open_tickets"]
    assert all(i["ticket_status"] in ("New", "In Progress", "Pending Customer", "On Hold") for i in r["items"])


def test_meta_and_data_quality():
    need_db()
    m = services.meta(psql_runner.run)
    assert len(m["teams"]) == 8 and "Network" in m["categories"] and m["min_date"] == "2024-01-01"
    d = services.data_quality(psql_runner.run)
    assert d["total_issues"] > 0 and any(r["rule_id"] == "BR-RULE-01" for r in d["rules"])


if __name__ == "__main__":
    import traceback
    tests = [(n, fn) for n, fn in sorted(globals().items()) if n.startswith("test_") and callable(fn)]
    failed = skipped = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Skip as e:
            skipped += 1
            print(f"SKIP {name}: {e}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}\n{traceback.format_exc()}")
    print(f"{len(tests) - failed - skipped} passed, {skipped} skipped, {failed} failed")
    sys.exit(1 if failed else 0)
