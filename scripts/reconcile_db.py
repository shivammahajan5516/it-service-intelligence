#!/usr/bin/env python3
"""
Independent reconciliation of the PostgreSQL KPIs (NFR-02).

Re-implements the business rules (docs/05_business_rules.md) in pandas,
straight from data/raw/*.csv, WITHOUT reusing any SQL, then compares the
results with the analytics views. Two independent implementations agreeing
is strong evidence that both are correct.

Requires psql on PATH and a built database (database/build_database.*).
Reads connection settings from .env. Writes data/reports/reconciliation.md.
Exit code 1 if any KPI differs by more than the tolerance.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TOL_PCT = 0.1     # percentage points
TOL_HOURS = 0.05  # hours
TOL_CSAT = 0.005


# ----------------------------------------------------------------- database side
def load_env():
    env = os.environ.copy()
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    env["PGHOST"] = env.get("DB_HOST", "localhost")
    env["PGPORT"] = env.get("DB_PORT", "5432")
    if env.get("DB_APP_USER"):
        env["PGUSER"] = env["DB_APP_USER"]
    if env.get("DB_APP_PASSWORD"):
        env["PGPASSWORD"] = env["DB_APP_PASSWORD"]
    return env, env.get("DB_NAME", "it_service_intelligence")


def sql(query: str) -> pd.DataFrame:
    env, db = load_env()
    out = subprocess.run(["psql", "-X", "-q", "--csv", "-d", db, "-c", query],
                         capture_output=True, text=True, env=env)
    if out.returncode != 0:
        sys.exit(f"psql failed: {out.stderr.strip()}")
    return pd.read_csv(io.StringIO(out.stdout))


# ----------------------------------------------------------------- pandas side
def pandas_fact() -> pd.DataFrame:
    t = pd.read_csv(RAW / "tickets.csv", dtype=str, keep_default_na=False, na_values=[""])
    cu = pd.read_csv(RAW / "customers.csv", dtype=str)
    sla = pd.read_csv(RAW / "sla_targets.csv")
    cat = pd.read_csv(RAW / "incident_categories.csv")

    t = t.drop_duplicates()                                    # exact duplicates
    t = t.sort_values(["ticket_id", "created_at"]).drop_duplicates("ticket_id")
    for c in ["created_at", "first_response_at", "resolved_at"]:
        t[c] = pd.to_datetime(t[c])
    num = lambda c: pd.to_numeric(t[c], errors="coerce")  # noqa: E731
    boo = lambda c: t[c].map({"true": True, "false": False})  # noqa: E731

    known = t["customer_id"].isin(cu["customer_id"])
    t["source_customer_id"] = t["customer_id"]
    t["customer_id"] = t["customer_id"].where(known, "CUST-UNKNOWN")
    t["sla_level"] = t["customer_id"].map(cu.set_index("customer_id")["sla_level"])
    lookup = sla.set_index(["sla_level", "priority"])
    t["target"] = num("sla_target_hours")
    derived = pd.Series([lookup["resolution_target_hours"].get((l, p), np.nan)
                         for l, p in zip(t["sla_level"], t["priority"])], index=t.index)
    t["target"] = t["target"].fillna(derived)
    t["rt"] = ((t["resolved_at"] - t["created_at"]).dt.total_seconds() / 3600).round(2)
    t["esc"] = boo("escalation_flag").fillna(False).astype(bool)
    t["reopen"] = num("reopened_count").fillna(0)
    t["fcr"] = boo("first_contact_resolution")
    csat = num("customer_satisfaction")
    t["csat"] = csat.where(csat.isin([1, 2, 3, 4, 5]))

    resolved = t["ticket_status"].isin(["Resolved", "Closed"])
    invalid = ((t["resolved_at"] < t["created_at"]) | (t["first_response_at"] < t["created_at"])
               | ((t["first_response_at"] > t["resolved_at"]) & (t["resolved_at"] >= t["created_at"]))
               | (resolved & t["resolved_at"].isna()))
    outlier = resolved & ~invalid & ((t["rt"] > 720) | (t["rt"] > 10 * t["target"]))

    # near-duplicates: same source customer + subcategory + priority within 15 min
    s = t[t["subcategory"].notna()].sort_values(["created_at", "ticket_id"])
    gap = s.groupby(["source_customer_id", "subcategory", "priority"])["created_at"].diff()
    dup_ids = set(s.loc[gap <= pd.Timedelta(minutes=15), "ticket_id"])
    f = t[~t["ticket_id"].isin(dup_ids)].copy()
    inv, out_ = invalid.loc[f.index], outlier.loc[f.index]
    res = resolved.loc[f.index]

    f["in_sla"] = res & ~inv & f["target"].notna()
    f["breach"] = np.where(f["in_sla"], f["rt"] > f["target"], np.nan)
    f["in_dur"] = f["in_sla"] & ~out_
    contradictory = (f["fcr"] == True) & (f["esc"] | (f["reopen"] > 0))  # noqa: E712
    f["fcr_ok"] = np.where(res & f["fcr"].notna() & ~contradictory, f["fcr"], np.nan)
    f["is_resolved"] = res
    f["is_open"] = f["ticket_status"].isin(["New", "In Progress", "Pending Customer", "On Hold"])

    sr = cat.set_index("subcategory")["is_service_request"]
    is_sr = f["subcategory"].map(sr)
    f["is_incident"] = np.where(is_sr.notna(), ~is_sr.fillna(False).astype(bool),
                                f["root_cause"] != "Service Request")
    eligible = f["is_incident"] & (f["customer_id"] != "CUST-UNKNOWN") & f["subcategory"].isin(cat["subcategory"])
    e = f[eligible].sort_values(["created_at", "ticket_id"])
    prev = e.groupby(["customer_id", "subcategory"])["created_at"].shift()
    rep = ((e["created_at"] - prev) <= pd.Timedelta(days=30))
    f["repeat"] = np.nan
    f.loc[e.index, "repeat"] = rep.astype(float)
    f["month"] = f["created_at"].dt.to_period("M").dt.to_timestamp()
    return f


def kpis(f: pd.DataFrame) -> dict:
    d = f[f["in_dur"]]["rt"]
    r = f[f["is_resolved"]]
    return {
        "total_tickets": len(f), "open_tickets": int(f["is_open"].sum()),
        "sla_breach_pct": 100 * f["breach"].mean(),
        "median_resolution_hours": d.median(), "mean_resolution_hours": d.mean(),
        "fcr_pct": 100 * f["fcr_ok"].mean(), "reopen_pct": 100 * (r["reopen"] > 0).mean(),
        "escalation_pct": 100 * f["esc"].mean(), "avg_csat": f["csat"].mean(),
        "repeat_incident_pct": 100 * f["repeat"].mean(),
    }


def tol(metric):
    if metric.endswith("_pct"):
        return TOL_PCT
    if "hours" in metric:
        return TOL_HOURS
    if metric == "avg_csat":
        return TOL_CSAT
    return 0


def main():
    f = pandas_fact()
    rows = []
    db = sql("SELECT * FROM analytics.kpi_overall").iloc[0]
    for k, v in kpis(f).items():
        rows.append(("overall", k, float(db[k]), float(v)))

    team_db = sql("SELECT team_id, sla_breach_pct, fcr_pct, tickets FROM analytics.kpi_team").set_index("team_id")
    for team, g in f.groupby("team_id"):
        rows.append((team, "tickets", float(team_db.loc[team, "tickets"]), float(len(g))))
        rows.append((team, "sla_breach_pct", float(team_db.loc[team, "sla_breach_pct"]), 100 * g["breach"].mean()))
        rows.append((team, "fcr_pct", float(team_db.loc[team, "fcr_pct"]), 100 * g["fcr_ok"].mean()))

    m_db = sql("SELECT created_month, sla_breach_pct, tickets FROM analytics.kpi_monthly")
    m_db["created_month"] = pd.to_datetime(m_db["created_month"])
    m_db = m_db.set_index("created_month")
    for month, g in f.groupby("month"):
        label = month.strftime("%Y-%m")
        rows.append((label, "tickets", float(m_db.loc[month, "tickets"]), float(len(g))))
        rows.append((label, "sla_breach_pct", float(m_db.loc[month, "sla_breach_pct"]), 100 * g["breach"].mean()))

    res = pd.DataFrame(rows, columns=["scope", "metric", "postgresql", "pandas"])
    res["abs_diff"] = (res["postgresql"] - res["pandas"]).abs().round(4)
    res["tolerance"] = res["metric"].map(tol)
    res["status"] = np.where(res["abs_diff"] <= res["tolerance"] + 1e-9, "PASS", "FAIL")

    lines = ["# Reconciliation: PostgreSQL vs independent pandas implementation", "",
             "Generated by `scripts/reconcile_db.py`. The pandas side re-implements the business rules "
             "directly from `data/raw/` without reusing any SQL. Tolerances: 0.1 percentage points, "
             "0.05 hours, 0.005 CSAT points (rounding in the SQL views), 0 for counts.", "",
             f"**{(res['status'] == 'PASS').sum()} of {len(res)} comparisons pass.**", "",
             "| Scope | Metric | PostgreSQL | pandas | Abs diff | Status |", "|---|---|---:|---:|---:|---|"]
    for r in res.itertuples():
        lines.append(f"| {r.scope} | {r.metric} | {r.postgresql:,.3f} | {r.pandas:,.3f} | {r.abs_diff} | {r.status} |")
    (ROOT / "data" / "reports" / "reconciliation.md").write_text("\n".join(lines) + "\n")

    failed = res[res["status"] == "FAIL"]
    print(f"Reconciliation: {len(res) - len(failed)}/{len(res)} comparisons within tolerance")
    print(res[res["scope"] == "overall"].to_string(index=False))
    if len(failed):
        print("\nFAILURES:\n" + failed.to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
