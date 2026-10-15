"""
Database tests (Phases 3-4). Require a built database and psql on PATH;
they are SKIPPED automatically when the database is not reachable.

    bash database/build_database.sh      # or build_database.ps1 on Windows
    pytest tests/test_database.py -q
"""
import io
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from reconcile_db import kpis, load_env, pandas_fact  # noqa: E402

try:
    import pytest
except ImportError:  # plain-python fallback runner
    class _P:
        class skip:
            class Exception(Exception):
                pass

        @staticmethod
        def fixture(**_):
            return lambda f: f

        @staticmethod
        def skip_(msg):
            raise _P.skip.Exception(msg)
    pytest = _P()


def q(sql, admin=False):
    env, db = load_env()
    if admin:
        for k in ("PGUSER", "PGPASSWORD"):
            env.pop(k, None)
        if env.get("DB_ADMIN_USER"):
            env["PGUSER"] = env["DB_ADMIN_USER"]
        if env.get("DB_ADMIN_PASSWORD"):
            env["PGPASSWORD"] = env["DB_ADMIN_PASSWORD"]
    r = subprocess.run(["psql", "-X", "-q", "--csv", "-d", db, "-c", sql],
                       capture_output=True, text=True, env=env)
    return r


def db_available():
    return shutil.which("psql") is not None and q("SELECT 1").returncode == 0


def _skip_if_no_db():
    if not db_available():
        msg = "PostgreSQL database not reachable - build it first"
        if hasattr(pytest, "skip_"):
            pytest.skip_(msg)
        pytest.skip(msg)


def frame(sql):
    r = q(sql)
    assert r.returncode == 0, r.stderr
    return pd.read_csv(io.StringIO(r.stdout))


def test_fact_row_count_matches_rules():
    _skip_if_no_db()
    n = frame("SELECT count(*) AS n FROM analytics.fact_tickets")["n"][0]
    assert n == kpis(pandas_fact())["total_tickets"]


def test_kpis_match_independent_pandas_implementation():
    _skip_if_no_db()
    db = frame("SELECT * FROM analytics.kpi_overall").iloc[0]
    py = kpis(pandas_fact())
    for k in ["sla_breach_pct", "fcr_pct", "reopen_pct", "escalation_pct", "repeat_incident_pct"]:
        assert abs(db[k] - py[k]) <= 0.1, k
    assert abs(db["median_resolution_hours"] - py["median_resolution_hours"]) <= 0.05
    assert abs(db["avg_csat"] - py["avg_csat"]) <= 0.005


def test_app_role_is_read_only():
    _skip_if_no_db()
    assert q("SELECT count(*) FROM clean.tickets").returncode != 0, "app role must not read clean"
    assert q("DELETE FROM analytics.fact_tickets").returncode != 0, "app role must not write"


def test_breach_and_compliance_sum_to_100():
    _skip_if_no_db()
    r = frame("SELECT sla_breach_pct + sla_compliance_pct AS s FROM analytics.kpi_overall")
    assert float(r["s"][0]) == 100.0


def test_pareto_is_monotonic_and_ends_at_100():
    _skip_if_no_db()
    r = frame("SELECT cumulative_pct FROM analytics.root_cause_pareto ORDER BY rank, root_cause")
    assert r["cumulative_pct"].is_monotonic_increasing
    assert float(r["cumulative_pct"].iloc[-1]) == 100.0


def test_no_duplicates_or_invalid_durations_in_kpis():
    _skip_if_no_db()
    r = frame("""SELECT count(*) FILTER (WHERE in_duration_population AND resolution_time_hours < 0) AS neg,
                        count(*) - count(DISTINCT ticket_id) AS dup
                 FROM analytics.fact_tickets""")
    assert r["neg"][0] == 0 and r["dup"][0] == 0


def test_all_analysis_queries_execute():
    _skip_if_no_db()
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_sql_analysis import parse_queries, run
    queries = parse_queries()
    assert len(queries) >= 30
    for item in queries:
        df, _ = run(item["sql"])
        assert len(df.columns) > 0, item["id"]


if __name__ == "__main__":
    import inspect
    import traceback
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = skipped = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except pytest.skip.Exception as e:  # type: ignore[attr-defined]
            skipped += 1
            print(f"SKIP {name}: {e}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}\n{traceback.format_exc()}")
    print(f"{len(tests) - failed - skipped} passed, {skipped} skipped, {failed} failed")
    sys.exit(1 if failed else 0)
