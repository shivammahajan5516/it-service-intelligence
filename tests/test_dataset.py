"""
Tests for the generated dataset (Phase 2).

Run: pytest tests/test_dataset.py -q
Assumes data/raw/ has been generated (bash scripts/regenerate_all.sh).
"""
import json
from pathlib import Path

import pandas as pd
try:
    import pytest
except ImportError:  # allow the plain-python fallback runner
    class _P:
        @staticmethod
        def fixture(**_):
            return lambda f: f
    pytest = _P()

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


@pytest.fixture(scope="module")
def d():
    names = ["tickets", "customers", "agents", "support_teams", "sla_targets", "calendar",
             "incident_categories"]
    return {n: pd.read_csv(RAW / f"{n}.csv", dtype=str, keep_default_na=False, na_values=[""])
            for n in names}


def test_row_counts_within_expected(d):
    exp = json.loads((ROOT / "data" / "expected_row_counts.json").read_text())
    for name, df in d.items():
        r = exp[f"{name}.csv"]
        assert r["min"] <= len(df) <= r["max"], name


def test_minimum_ticket_volume(d):
    assert len(d["tickets"]) >= 20_000


def test_dimension_primary_keys_unique(d):
    for name, pk in [("customers", "customer_id"), ("agents", "agent_id"),
                     ("support_teams", "team_id"), ("sla_targets", "sla_rule_id"),
                     ("calendar", "date_key"), ("incident_categories", "subcategory_id")]:
        assert d[name][pk].is_unique and d[name][pk].notna().all(), name


def test_dimension_foreign_keys(d):
    assert d["agents"]["team_id"].isin(d["support_teams"]["team_id"]).all()
    assert d["incident_categories"]["default_team_id"].isin(d["support_teams"]["team_id"]).all()
    assert d["support_teams"]["team_lead_agent_id"].isin(d["agents"]["agent_id"]).all()


def test_headcount_matches_agents(d):
    hc = d["support_teams"].set_index("team_id")["planned_headcount"].astype(int)
    actual = d["agents"].groupby("team_id").size()
    assert (hc == actual).all()


def test_sla_rules_complete(d):
    s = d["sla_targets"]
    assert len(s.drop_duplicates(["sla_level", "priority"])) == 16
    tgt = s.astype({"resolution_target_hours": float}).pivot(index="sla_level", columns="priority",
                                                            values="resolution_target_hours")
    # targets loosen with priority number for every level
    assert (tgt.diff(axis=1).iloc[:, 1:] >= 0).all().all()


def test_calendar_covers_ticket_period(d):
    cal = pd.to_datetime(d["calendar"]["date"])
    created = pd.to_datetime(d["tickets"]["created_at"])
    assert cal.diff().dropna().dt.days.eq(1).all()
    assert created.min() >= cal.min() and created.max() < cal.max() + pd.Timedelta(days=1)


def test_data_quality_issues_are_controlled(d):
    """Issues exist (so cleaning has work to do) but stay small (dataset stays usable)."""
    t = d["tickets"]
    bad_cat = (~t["category"].isin(d["incident_categories"]["category"])).mean()
    assert 0.005 < bad_cat < 0.05
    orphan = (~t["customer_id"].isin(d["customers"]["customer_id"])).sum()
    assert 0 < orphan < 50
    csat = pd.to_numeric(t["customer_satisfaction"], errors="coerce")
    assert 0 < (csat.notna() & ~csat.isin([1, 2, 3, 4, 5])).mean() < 0.01
    assert t.duplicated().sum() > 0


def test_injection_log_references_real_tickets(d):
    log = pd.read_csv(ROOT / "data" / "reference" / "dq_injection_log.csv")
    assert log["ticket_id"].isin(d["tickets"]["ticket_id"]).all()


def test_built_in_patterns_present(d):
    """Sanity-check that the documented mechanisms produced signal."""
    t = d["tickets"].drop_duplicates()
    t = t[t["ticket_status"].isin(["Resolved", "Closed"])].copy()
    t["rt"] = pd.to_numeric(t["resolution_time_hours"])
    t["tgt"] = pd.to_numeric(t["sla_target_hours"])
    t = t[(t["rt"] >= 0) & (t["rt"] < 720) & t["tgt"].notna()]
    med = t.groupby("priority")["rt"].median()
    assert med["P1"] < med["P2"] < med["P3"] < med["P4"]
    t["breach"] = t["rt"] > t["tgt"]
    yr = t.groupby(pd.to_datetime(t["created_at"]).dt.year)["breach"].mean()
    assert yr[2025] > yr[2024]
    csat = pd.to_numeric(t["customer_satisfaction"], errors="coerce")
    ok = csat.between(1, 5)
    assert csat[ok & t["breach"]].mean() < csat[ok & ~t["breach"]].mean() - 0.5


def test_manifest_hashes_match_files():
    import hashlib
    m = json.loads((RAW / "manifest.json").read_text())
    for name, meta in m["files"].items():
        h = hashlib.sha256((RAW / name).read_bytes()).hexdigest()
        assert h == meta["sha256"], name


if __name__ == "__main__":
    # Fallback runner for environments without pytest: python tests/test_dataset.py
    import inspect
    import sys
    import traceback

    data = d.__wrapped__() if hasattr(d, "__wrapped__") else None
    if data is None:
        names = ["tickets", "customers", "agents", "support_teams", "sla_targets", "calendar",
                 "incident_categories"]
        data = {n: pd.read_csv(RAW / f"{n}.csv", dtype=str, keep_default_na=False, na_values=[""])
                for n in names}
    failed = 0
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        try:
            fn(data) if inspect.signature(fn).parameters else fn()
            print(f"PASS {name}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}\n{traceback.format_exc()}")
    print(f"{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
