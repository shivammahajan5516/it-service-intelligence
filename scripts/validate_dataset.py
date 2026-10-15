#!/usr/bin/env python3
"""
Validate the raw synthetic extract in data/raw/.

Two classes of check:

  STRUCTURAL (FAIL stops the pipeline) - files, columns, row counts,
      dimension primary keys and dimension-to-dimension foreign keys,
      SLA rule coverage, calendar coverage.

  DATA QUALITY (WARN - expected in a raw extract) - duplicates, orphan
      keys, label inconsistencies, missing values, invalid timestamps,
      outliers, out-of-range scores, contradictory flags. These are
      documented, quantified and handed to the cleaning layer.

The checks are written WITHOUT reading the injection answer key. At the
end the detected counts are compared with data/reference/
dq_injection_log.csv to report how many injected issues each check found.

Outputs (data/reports/):
    validation_report.md        human-readable summary
    dq_checks.csv               one row per check
    missing_values.csv          per table / column
    duplicate_report.csv        exact + near-duplicate tickets
    records_for_investigation.csv  ticket-level exceptions
Exit code 1 if any STRUCTURAL check fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_COLUMNS = {
    "tickets.csv": ["ticket_id", "customer_id", "agent_id", "team_id", "created_at",
                    "first_response_at", "resolved_at", "priority", "category", "subcategory",
                    "channel", "ticket_status", "sla_target_hours", "first_response_time_hours",
                    "resolution_time_hours", "escalation_flag", "reopened_count",
                    "first_contact_resolution", "customer_satisfaction", "root_cause",
                    "resolution_type", "business_impact", "knowledge_base_used", "region"],
    "customers.csv": ["customer_id", "customer_name", "industry", "company_size", "region",
                      "contract_type", "sla_level", "customer_since", "customer_success_manager"],
    "agents.csv": ["agent_id", "agent_name", "team_id", "experience_level", "shift", "location",
                   "employment_type", "start_date"],
    "support_teams.csv": ["team_id", "team_name", "support_tier", "primary_location",
                          "operating_model", "planned_headcount", "team_lead_agent_id"],
    "sla_targets.csv": ["sla_rule_id", "sla_level", "priority", "response_target_hours",
                        "resolution_target_hours", "clock_basis", "effective_from", "effective_to"],
    "calendar.csv": ["date_key", "date", "year", "quarter", "month", "month_name", "year_month",
                     "iso_year", "iso_week", "day_of_month", "day_of_week", "day_name",
                     "is_weekend", "is_uk_bank_holiday", "holiday_name", "is_working_day",
                     "fiscal_year", "fiscal_quarter"],
    "incident_categories.csv": ["subcategory_id", "category_id", "category", "subcategory",
                                "default_team_id", "complexity_tier", "is_service_request"],
}
OPTIONAL_TICKET_COLS = {"first_response_at", "resolved_at", "first_response_time_hours",
                        "resolution_time_hours", "first_contact_resolution",
                        "customer_satisfaction", "root_cause", "resolution_type",
                        "knowledge_base_used", "agent_id", "subcategory", "channel",
                        "sla_target_hours"}
VALID = {
    "priority": {"P1", "P2", "P3", "P4"},
    "channel": {"Portal", "Email", "Phone", "Chat", "Monitoring Alert"},
    "ticket_status": {"New", "In Progress", "Pending Customer", "On Hold", "Resolved",
                      "Closed", "Cancelled"},
    "business_impact": {"Critical", "High", "Medium", "Low"},
}
OPEN_STATUSES = {"New", "In Progress", "Pending Customer", "On Hold"}
DONE_STATUSES = {"Resolved", "Closed"}


class Checker:
    def __init__(self):
        self.rows = []

    def add(self, check_id, kind, table, description, n_flagged, total, status=None,
            detail=""):
        if status is None:
            status = "PASS" if n_flagged == 0 else ("FAIL" if kind == "STRUCTURAL" else "WARN")
        self.rows.append({"check_id": check_id, "kind": kind, "table": table,
                          "description": description, "records_flagged": int(n_flagged),
                          "total_records": int(total),
                          "pct_flagged": round(100 * n_flagged / total, 3) if total else 0.0,
                          "status": status, "detail": detail})

    def df(self):
        return pd.DataFrame(self.rows)


def load(raw: Path):
    out = {}
    for name in EXPECTED_COLUMNS:
        p = raw / name
        out[name] = pd.read_csv(p, dtype=str, keep_default_na=False, na_values=[""]) if p.exists() else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    args = ap.parse_args()
    raw, reports = args.data / "raw", args.data / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    expected = json.loads((args.data / "expected_row_counts.json").read_text())
    ck = Checker()
    d = load(raw)

    # ---------------- STRUCTURAL ----------------
    for name, cols in EXPECTED_COLUMNS.items():
        df = d[name]
        if df is None:
            ck.add("S01", "STRUCTURAL", name, "File exists", 1, 1)
            continue
        missing = [c for c in cols if c not in df.columns]
        ck.add("S02", "STRUCTURAL", name, "Expected columns present", len(missing), len(cols),
               detail=", ".join(missing))
        lo, hi = expected[name]["min"], expected[name]["max"]
        ok = lo <= len(df) <= hi
        ck.add("S03", "STRUCTURAL", name, f"Row count within [{lo}, {hi}]", 0 if ok else 1, 1,
               detail=f"actual={len(df)}")
    if any(r["status"] == "FAIL" and r["check_id"] == "S01" for r in ck.rows):
        ck.df().to_csv(reports / "dq_checks.csv", index=False)
        print("Missing files - aborting.")
        sys.exit(1)

    t, cu, ag = d["tickets.csv"], d["customers.csv"], d["agents.csv"]
    tm, sla, cal, cat = (d["support_teams.csv"], d["sla_targets.csv"], d["calendar.csv"],
                         d["incident_categories.csv"])

    for name, df, pk in [("customers.csv", cu, "customer_id"), ("agents.csv", ag, "agent_id"),
                         ("support_teams.csv", tm, "team_id"), ("sla_targets.csv", sla, "sla_rule_id"),
                         ("calendar.csv", cal, "date"), ("incident_categories.csv", cat, "subcategory_id")]:
        dup = df[pk].duplicated().sum() + df[pk].isna().sum()
        ck.add("S04", "STRUCTURAL", name, f"Primary key {pk} unique and not null", dup, len(df))

    for child, df, col, parent, pcol in [
        ("agents.csv", ag, "team_id", tm, "team_id"),
        ("support_teams.csv", tm, "team_lead_agent_id", ag, "agent_id"),
        ("incident_categories.csv", cat, "default_team_id", tm, "team_id")]:
        bad = (~df[col].isin(parent[pcol])).sum()
        ck.add("S05", "STRUCTURAL", child, f"FK {col} -> {pcol}", bad, len(df))

    combos = sla.groupby(["sla_level", "priority"]).size()
    ck.add("S06", "STRUCTURAL", "sla_targets.csv", "Exactly one rule per sla_level x priority (16)",
           int((combos != 1).sum() + (16 - len(combos))), 16)
    bad_lvl = (~cu["sla_level"].isin(sla["sla_level"])).sum()
    ck.add("S07", "STRUCTURAL", "customers.csv", "sla_level has a matching SLA rule", bad_lvl, len(cu))

    cal_dates = pd.to_datetime(cal["date"])
    gaps = int((cal_dates.diff().dt.days.dropna() != 1).sum())
    ck.add("S08", "STRUCTURAL", "calendar.csv", "Calendar contiguous (no gaps)", gaps, len(cal))

    created = pd.to_datetime(t["created_at"], errors="coerce")
    fr = pd.to_datetime(t["first_response_at"], errors="coerce")
    res = pd.to_datetime(t["resolved_at"], errors="coerce")
    out_cal = ((created < cal_dates.min()) | (created >= cal_dates.max() + pd.Timedelta(days=1))).sum()
    ck.add("S09", "STRUCTURAL", "tickets.csv", "All created_at dates covered by calendar",
           out_cal, len(t))
    unparsable = int(created.isna().sum())
    ck.add("S10", "STRUCTURAL", "tickets.csv", "created_at present and parseable", unparsable, len(t))

    # ---------------- DATA QUALITY ----------------
    n = len(t)
    exceptions = []

    def flag(mask, check_id, kind_desc, table="tickets.csv", desc=None, record=True):
        mask = pd.Series(mask, index=t.index).fillna(False).astype(bool)
        ck.add(check_id, "DATA QUALITY", table, desc or kind_desc, int(mask.sum()), n)
        if record and mask.any():
            exceptions.append(pd.DataFrame({"ticket_id": t.loc[mask, "ticket_id"],
                                            "check_id": check_id, "issue": kind_desc}))
        return mask

    # duplicates
    exact = t.duplicated(keep="first")
    flag(exact, "D01", "Exact duplicate row (double-loaded extract)")
    dup_id = t["ticket_id"].duplicated(keep=False) & ~t.duplicated(keep=False)
    flag(dup_id, "D02", "ticket_id reused with different content")
    u = t[~exact].copy()
    u["_created"] = pd.to_datetime(u["created_at"])
    u = u.sort_values(["customer_id", "subcategory", "_created"])
    same = (u["customer_id"].eq(u["customer_id"].shift()) & u["subcategory"].eq(u["subcategory"].shift())
            & u["priority"].eq(u["priority"].shift()) & u["subcategory"].notna())
    gap_min = (u["_created"] - u["_created"].shift()).dt.total_seconds() / 60
    near = same & (gap_min <= 15)
    near_ids = u.loc[near, "ticket_id"]
    prev_ids = u["ticket_id"].shift().loc[near]
    flag(t["ticket_id"].isin(near_ids) & ~exact, "D03",
         "Near-duplicate: same customer, subcategory and priority within 15 minutes")
    dup_report = pd.concat([
        pd.DataFrame({"duplicate_type": "exact_row", "ticket_id": t.loc[exact, "ticket_id"],
                      "matches_ticket_id": t.loc[exact, "ticket_id"], "minutes_apart": 0.0}),
        pd.DataFrame({"duplicate_type": "near_duplicate", "ticket_id": near_ids.values,
                      "matches_ticket_id": prev_ids.values,
                      "minutes_apart": gap_min.loc[near].round(1).values})], ignore_index=True)
    dup_report.to_csv(reports / "duplicate_report.csv", index=False)

    # referential integrity from the fact table
    flag(~t["customer_id"].isin(cu["customer_id"]), "R01", "Orphan customer_id (not in customers)")
    flag(t["agent_id"].notna() & ~t["agent_id"].isin(ag["agent_id"]), "R02", "Orphan agent_id")
    flag(~t["team_id"].isin(tm["team_id"]), "R03", "Orphan team_id")
    team_of = ag.set_index("agent_id")["team_id"]
    flag(t["agent_id"].notna() & (t["agent_id"].map(team_of) != t["team_id"]), "R04",
         "Agent does not belong to the ticket's resolver team")
    flag(t["agent_id"].isna() & t["ticket_status"].isin(DONE_STATUSES), "R05",
         "Resolved/closed ticket with no agent recorded")

    # controlled vocabularies
    flag(~t["category"].isin(cat["category"]), "V01", "Category label not in controlled list")
    flag(t["subcategory"].notna() & ~t["subcategory"].isin(cat["subcategory"]), "V02",
         "Subcategory not in controlled list")
    pair_ok = set(zip(cat["category"], cat["subcategory"]))
    clean_cat = t["category"].isin(cat["category"])
    flag(clean_cat & t["subcategory"].notna() &
         ~pd.Series(list(zip(t["category"], t["subcategory"]))).isin(pair_ok), "V03",
         "Category / subcategory pair not in hierarchy")
    flag(~t["region"].isin(cu["region"].dropna().unique()), "V04", "Region label not in standard list")
    for col, vals in VALID.items():
        flag(t[col].notna() & ~t[col].isin(vals), f"V05-{col}", f"Invalid {col} value")

    # missing values
    mv = []
    for name, df in d.items():
        for col in df.columns:
            k = int(df[col].isna().sum())
            mv.append({"table": name, "column": col, "missing": k, "rows": len(df),
                       "pct_missing": round(100 * k / len(df), 2),
                       "column_type": ("optional" if (name == "tickets.csv" and col in OPTIONAL_TICKET_COLS)
                                       or col in ("holiday_name", "effective_to") else "required")})
    mv = pd.DataFrame(mv)
    mv.to_csv(reports / "missing_values.csv", index=False)
    req_missing = mv[(mv["column_type"] == "required") & (mv["missing"] > 0)]
    ck.add("M01", "DATA QUALITY", "all", "Missing values in required columns",
           int(req_missing["missing"].sum()), int(mv["rows"].sum()),
           detail="; ".join(f"{r.table}.{r.column}={r.missing}" for r in req_missing.itertuples()))
    done = t["ticket_status"].isin(DONE_STATUSES)
    flag(done & t["root_cause"].isna(), "M02", "Resolved/closed ticket missing root_cause")
    flag(t["knowledge_base_used"].isna(), "M03", "knowledge_base_used not recorded")
    flag(t["channel"].isna(), "M04", "channel missing")
    flag(t["subcategory"].isna(), "M05", "subcategory missing")
    flag(t["sla_target_hours"].isna(), "M06", "sla_target_hours missing (derivable from SLA rules)")

    # lifecycle / timestamp validity
    flag(done & res.isna(), "T01", "Resolved/closed ticket without resolved_at")
    flag(t["ticket_status"].isin(OPEN_STATUSES) & res.notna(), "T02", "Open ticket with resolved_at")
    flag(res.notna() & (res < created), "T03", "resolved_at earlier than created_at")
    flag(fr.notna() & (fr < created), "T04", "first_response_at earlier than created_at")
    flag(fr.notna() & res.notna() & (fr > res) & (res >= created), "T05",
         "first_response_at later than resolved_at")
    snap = pd.Timestamp("2025-12-31 23:59:59")
    flag((created > snap) | (res > snap) | (fr > snap), "T06", "Timestamp after extract snapshot")
    calc = ((res - created).dt.total_seconds() / 3600).round(2)
    stored = pd.to_numeric(t["resolution_time_hours"], errors="coerce")
    flag(stored.notna() & ((calc - stored).abs() > 0.011), "T07",
         "resolution_time_hours inconsistent with timestamps")

    # outliers (valid, closed incidents): robust per-priority rule
    rt = pd.to_numeric(t["resolution_time_hours"], errors="coerce")
    valid_rt = done & (rt >= 0)
    q = t[valid_rt].assign(rt=rt[valid_rt]).groupby("priority")["rt"].quantile([.25, .75]).unstack()
    log_rt = np.log1p(rt.where(valid_rt))
    lq = t[valid_rt].assign(l=log_rt[valid_rt]).groupby("priority")["l"].quantile([.25, .75]).unstack()
    upper = (lq[.75] + 1.5 * (lq[.75] - lq[.25]))
    out_mask = valid_rt & (log_rt > t["priority"].map(upper))
    flag(out_mask, "O01", "Statistical outlier: log resolution time above Tukey fence (Q3 + 1.5 IQR) within priority",
         record=False)
    target = pd.to_numeric(t["sla_target_hours"], errors="coerce")
    extreme = valid_rt & ((rt > 720) | (target.notna() & (rt > 10 * target)))
    flag(extreme, "O02", "Business-rule outlier: resolution > 30 days or > 10x SLA target (likely not closed on time)")
    p995 = rt[valid_rt].quantile(.995)
    ck.add("O03", "DATA QUALITY", "tickets.csv", f"Info: 99.5th percentile resolution = {p995:.1f} h",
           0, n, status="INFO")

    # scores and flags
    csat = pd.to_numeric(t["customer_satisfaction"], errors="coerce")
    flag(csat.notna() & ~csat.isin([1, 2, 3, 4, 5]), "C01", "Customer satisfaction outside 1-5 scale")
    flag(csat.notna() & ~done, "C02", "Satisfaction recorded on a ticket that is not resolved/closed")
    fcr = t["first_contact_resolution"] == "true"
    flag(fcr & (t["escalation_flag"] == "true"), "F01", "FCR = true but ticket was escalated")
    flag(fcr & (pd.to_numeric(t["reopened_count"]) > 0), "F02", "FCR = true but ticket was reopened")
    flag((t["priority"] == "P1") & (t["business_impact"] == "Low"), "F03",
         "P1 priority with Low business impact")
    lookup = sla.assign(k=sla["sla_level"] + "|" + sla["priority"]).set_index("k")["resolution_target_hours"]
    lvl = t["customer_id"].map(cu.set_index("customer_id")["sla_level"])
    expected_target = (lvl + "|" + t["priority"]).map(lookup)
    flag(t["sla_target_hours"].notna() & expected_target.notna()
         & (pd.to_numeric(t["sla_target_hours"]) != pd.to_numeric(expected_target)), "F04",
         "sla_target_hours differs from SLA rule for customer level and priority")
    since = pd.to_datetime(t["customer_id"].map(cu.set_index("customer_id")["customer_since"]))
    flag(since.notna() & (created.dt.normalize() < since), "F05", "Ticket created before customer_since")

    # ---------------- outputs ----------------
    checks = ck.df()
    checks.to_csv(reports / "dq_checks.csv", index=False)
    exc = pd.concat(exceptions, ignore_index=True) if exceptions else pd.DataFrame(
        columns=["ticket_id", "check_id", "issue"])
    exc.to_csv(reports / "records_for_investigation.csv", index=False)

    # detection vs injection answer key
    key_path = args.data / "reference" / "dq_injection_log.csv"
    recall_rows = []
    if key_path.exists():
        key = pd.read_csv(key_path)
        mapping = {"inconsistent_category_label": ["V01"], "inconsistent_region_label": ["V04"],
                   "missing_agent": ["R05"], "resolution_time_outlier": ["O02"],
                   "invalid_timestamp_resolved_before_created": ["T03"],
                   "invalid_timestamp_response_before_created": ["T04"],
                   "invalid_timestamp_response_after_resolved": ["T05"],
                   "invalid_satisfaction_score": ["C01"], "agent_team_mismatch": ["R04"],
                   "contradictory_fcr_escalated": ["F01"], "contradictory_fcr_reopened": ["F02"],
                   "priority_impact_mismatch": ["F03"], "orphan_customer_id": ["R01"],
                   "closed_without_resolved_at": ["T01"], "near_duplicate_ticket": ["D03"],
                   "exact_duplicate_row": ["D01"]}
        mk = key[key["issue_type"] == "missing_optional_value"]
        for col, cid in [("root_cause", "M02"), ("knowledge_base_used", "M03"), ("channel", "M04"),
                         ("subcategory", "M05"), ("sla_target_hours", "M06")]:
            mapping[f"missing:{col}"] = [cid]
        key.loc[key["issue_type"] == "missing_optional_value", "issue_type"] = \
            "missing:" + mk["column"]
        for issue, ids in key.groupby("issue_type")["ticket_id"]:
            cids = mapping.get(issue, [])
            found = exc[exc["check_id"].isin(cids)]["ticket_id"]
            injected = set(ids)
            hit = len(injected & set(found))
            recall_rows.append({"injected_issue": issue, "check_ids": ",".join(cids),
                                "injected": len(injected), "detected": hit,
                                "detection_rate_pct": round(100 * hit / len(injected), 1)})
    recall = pd.DataFrame(recall_rows)

    structural_fail = checks[(checks["kind"] == "STRUCTURAL") & (checks["status"] == "FAIL")]
    write_report(reports / "validation_report.md", checks, mv, dup_report, exc, recall, d,
                 structural_fail.empty)
    s = checks["status"].value_counts().to_dict()
    print(f"Checks: {len(checks)}  " + "  ".join(f"{k}={v}" for k, v in sorted(s.items())))
    print(f"Ticket-level exceptions: {exc['ticket_id'].nunique():,} tickets "
          f"({100 * exc['ticket_id'].nunique() / n:.1f}% of rows)")
    if not recall.empty:
        print(f"Injected issues detected: {recall['detected'].sum():,} / {recall['injected'].sum():,}")
    if not structural_fail.empty:
        print("STRUCTURAL FAILURES:\n" + structural_fail.to_string(index=False))
        sys.exit(1)
    print("Structural validation PASSED")


def write_report(path, checks, mv, dup, exc, recall, d, passed):
    L = ["# Dataset validation report", "",
         "Generated by `scripts/validate_dataset.py` against `data/raw/`. "
         "All data is synthetic.", "",
         f"**Structural validation: {'PASSED' if passed else 'FAILED'}**", "",
         "## Row counts", "", "| File | Rows | Columns |", "|---|---:|---:|"]
    for name, df in d.items():
        L.append(f"| {name} | {len(df):,} | {len(df.columns)} |")
    L += ["", "## Structural checks", "", "| ID | Table | Check | Flagged | Status |",
          "|---|---|---|---:|---|"]
    for r in checks[checks["kind"] == "STRUCTURAL"].itertuples():
        L.append(f"| {r.check_id} | {r.table} | {r.description} | {r.records_flagged} | {r.status} |")
    L += ["", "## Data-quality checks (tickets unless stated)", "",
          "| ID | Check | Flagged | % of rows | Status |", "|---|---|---:|---:|---|"]
    for r in checks[checks["kind"] == "DATA QUALITY"].itertuples():
        L.append(f"| {r.check_id} | {r.description} | {r.records_flagged:,} | {r.pct_flagged} | {r.status} |")
    L += ["", "## Missing values (columns with any missing)", "",
          "| Table | Column | Missing | % | Type |", "|---|---|---:|---:|---|"]
    for r in mv[mv["missing"] > 0].sort_values(["table", "pct_missing"], ascending=[True, False]).itertuples():
        L.append(f"| {r.table} | {r.column} | {r.missing:,} | {r.pct_missing} | {r.column_type} |")
    L += ["", "Note: `customer_satisfaction` is mostly missing by design - survey non-response, "
          "not a defect. `resolved_at` / `resolution_time_hours` are empty for open tickets.", "",
          "## Duplicates", "",
          f"- Exact duplicate rows: {int((dup['duplicate_type'] == 'exact_row').sum())}",
          f"- Near-duplicate tickets: {int((dup['duplicate_type'] == 'near_duplicate').sum())} "
          "(same customer + subcategory + priority within 15 minutes)",
          "", "Full list: `duplicate_report.csv`.", "",
          "## Records requiring investigation", "",
          f"{exc['ticket_id'].nunique():,} distinct tickets carry at least one exception "
          "(`records_for_investigation.csv`).", ""]
    if not recall.empty:
        L += ["## Detection of injected issues", "",
              "The generator logs every issue it injects (`data/reference/dq_injection_log.csv`). "
              "The checks above were written without using that log; this table measures them against it.",
              "", "| Injected issue | Check | Injected | Detected | Rate |", "|---|---|---:|---:|---:|"]
        for r in recall.itertuples():
            L.append(f"| {r.injected_issue} | {r.check_ids} | {r.injected} | {r.detected} | {r.detection_rate_pct}% |")
        L += ["", "Rates below 100% are explained in `docs/06_synthetic_data_design.md` "
              "(e.g. an outlier injected into a very short P1 ticket can stay below the "
              "'> 30 days or > 10x target' threshold)."]
    path.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
