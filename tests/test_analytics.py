"""
Tests for analytical calculations (Phase 5).
Run: pytest tests/test_analytics.py -q   (or: python tests/test_analytics.py)
Requires data/processed/ (created by database/build_database.*; also shipped in the zip).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analytics"))
from cleaning import clean_tickets, kpi_population  # noqa: E402
from common import cramers_v, load_fact, wilson_ci  # noqa: E402
import model  # noqa: E402


def test_wilson_interval_known_values():
    lo, hi = wilson_ci(10, 100)
    assert abs(lo - 0.0552) < 1e-3 and abs(hi - 0.1744) < 1e-3
    lo, hi = wilson_ci(0, 20)
    assert lo == 0 or abs(lo) < 1e-12
    assert 0 < hi < 0.2


def test_cramers_v_bounds():
    perfect = pd.DataFrame([[50, 0], [0, 50]])
    none = pd.DataFrame([[25, 25], [25, 25]])
    assert abs(cramers_v(perfect) - 1) < 1e-9
    assert cramers_v(none) < 1e-9


def test_pandas_cleaning_matches_sql_fact_table():
    t, log = clean_tickets()
    pop = kpi_population(t)
    f = load_fact()
    assert set(pop["ticket_id"]) == set(f["ticket_id"])
    assert abs(pop["sla_breached"].astype(float).mean() - f["sla_breached"].astype(float).mean()) < 1e-9
    assert {"BR-RULE-01", "BR-RULE-06", "BR-RULE-08", "BR-RULE-12"} <= set(log["rule"])


def test_breach_rate_definition():
    f = load_fact()
    s = f[f["in_sla_population"]]
    manual = (s["resolution_time_hours"] > s["sla_target_hours"]).mean()
    assert abs(manual - s["sla_breached"].astype(float).mean()) < 1e-12
    # outside the population the outcome is undefined, never False
    assert f.loc[~f["in_sla_population"], "sla_breached"].isna().all()


def test_model_features_exclude_post_creation_information():
    leaky = {"resolution_time_hours", "first_response_time_hours", "escalation_flag", "reopened_count",
             "first_contact_resolution", "root_cause", "resolution_type", "knowledge_base_used",
             "customer_satisfaction", "ticket_status", "resolved_at", "first_response_at", "sla_breached"}
    assert not leaky & set(model.CAT + model.NUM)


def test_customer_history_uses_only_earlier_outcomes():
    f = load_fact()
    dims = model.load_dims()
    d = model.build_features(f, dims)
    # first ticket of every customer has no prior tickets and no prior resolved breaches
    first = d.sort_values("created_at").groupby("customer_id").head(1)
    assert (first["cust_prior_tickets"] == 0).all()
    assert (first["cust_prior_resolved"] == 0).all()
    # prior resolved count can never exceed prior ticket count
    assert (d["cust_prior_resolved"] <= d["cust_prior_tickets"]).all()


if __name__ == "__main__":
    import traceback
    tests = [(n, fn) for n, fn in sorted(globals().items()) if n.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}\n{traceback.format_exc()}")
    print(f"{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
