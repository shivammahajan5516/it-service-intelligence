"""
Phase 5 data cleaning in pandas: raw CSV -> analysis-ready ticket table.

This is a second, independent implementation of docs/05_business_rules.md
(the first is database/transform_clean.sql + analytics_views.sql). It records
how many rows each step affected so the cleaning is auditable, and
run_analysis.py checks that it reproduces the PostgreSQL fact table exactly.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from common import RAW

SYNONYMS = {"Netwrk": "Network", "H/W": "Hardware", "SW": "Software", "Infra": "Infrastructure",
            "Cloud": "Cloud Services", "Business Apps": "Business Applications",
            "Cyber Security": "Security", "DB": "Database"}
OPEN = ["New", "In Progress", "Pending Customer", "On Hold"]
DONE = ["Resolved", "Closed"]


def _norm(label: str) -> str:
    return re.sub(r"[^a-z]", "", label.lower().replace(" and ", " "))


def clean_tickets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (clean tickets incl. duplicates flagged, step log)."""
    log = []

    def step(name, rule, n):
        log.append({"step": name, "rule": rule, "rows_affected": int(n)})

    t = pd.read_csv(RAW / "tickets.csv", dtype=str, keep_default_na=False, na_values=[""])
    cu = pd.read_csv(RAW / "customers.csv", dtype=str)
    sla = pd.read_csv(RAW / "sla_targets.csv")
    cat = pd.read_csv(RAW / "incident_categories.csv")
    step("Raw rows loaded", "-", len(t))

    before = len(t)
    t = t.drop_duplicates()
    step("Exact duplicate rows collapsed", "BR-RULE-01", before - len(t))
    t = t.sort_values(["ticket_id", "created_at"]).drop_duplicates("ticket_id").reset_index(drop=True)

    # types
    for c in ["created_at", "first_response_at", "resolved_at"]:
        t[c] = pd.to_datetime(t[c], errors="coerce")
    for c in ["sla_target_hours", "reopened_count", "customer_satisfaction"]:
        t[c] = pd.to_numeric(t[c], errors="coerce")
    for c in ["escalation_flag", "first_contact_resolution", "knowledge_base_used"]:
        t[c] = t[c].map({"true": True, "false": False})
    t["escalation_flag"] = t["escalation_flag"].fillna(False).astype(bool)
    t["reopened_count"] = t["reopened_count"].fillna(0)

    # category standardisation
    controlled = {_norm(c): c for c in cat["category"].unique()}
    std = t["category"].map(lambda x: x if x in controlled.values()
                            else controlled.get(_norm(x), SYNONYMS.get(x)))
    step("Category labels standardised", "BR-RULE-12", (std != t["category"]).sum())
    t["category_raw"], t["category"] = t["category"], std

    regions = set(cu["region"].dropna())
    lookup = {r.lower(): r for r in regions}
    reg = t["region"].str.strip().str.lower().map(lookup).fillna("Unknown")
    step("Region labels standardised", "V04", (reg != t["region"]).sum())
    t["region"] = reg

    # orphans, SLA level and targets
    orphan = ~t["customer_id"].isin(cu["customer_id"])
    step("Orphan customer_id -> CUST-UNKNOWN", "BR-RULE-13", orphan.sum())
    t["source_customer_id"] = t["customer_id"]
    t.loc[orphan, "customer_id"] = "CUST-UNKNOWN"
    t["sla_level"] = t["customer_id"].map(cu.set_index("customer_id")["sla_level"])
    s = sla.set_index(["sla_level", "priority"])
    keys = list(zip(t["sla_level"], t["priority"]))
    derived = pd.Series([s["resolution_target_hours"].get(k, np.nan) for k in keys], index=t.index)
    missing_target = t["sla_target_hours"].isna() & derived.notna()
    step("Missing SLA target derived from rules", "BR-RULE-15", missing_target.sum())
    t["sla_target_hours"] = t["sla_target_hours"].fillna(derived)
    t["response_target_hours"] = [s["response_target_hours"].get(k, np.nan) for k in keys]

    # durations recomputed from timestamps
    t["first_response_time_hours"] = ((t["first_response_at"] - t["created_at"]).dt.total_seconds() / 3600).round(2)
    t["resolution_time_hours"] = ((t["resolved_at"] - t["created_at"]).dt.total_seconds() / 3600).round(2)

    done = t["ticket_status"].isin(DONE)
    invalid = ((t["resolved_at"] < t["created_at"]) | (t["first_response_at"] < t["created_at"])
               | ((t["first_response_at"] > t["resolved_at"]) & (t["resolved_at"] >= t["created_at"]))
               | (done & t["resolved_at"].isna()))
    step("Invalid timestamps flagged", "BR-RULE-06", invalid.sum())
    t["is_invalid_timestamp"] = invalid

    outlier = done & ~invalid & ((t["resolution_time_hours"] > 720)
                                 | (t["resolution_time_hours"] > 10 * t["sla_target_hours"]))
    step("Resolution outliers flagged", "BR-RULE-08", outlier.sum())
    t["is_resolution_outlier"] = outlier

    bad_csat = t["customer_satisfaction"].notna() & ~t["customer_satisfaction"].isin([1, 2, 3, 4, 5])
    step("Out-of-range CSAT set to missing", "BR-RULE-07", bad_csat.sum())
    t.loc[bad_csat, "customer_satisfaction"] = np.nan

    contra = (t["first_contact_resolution"] == True) & (t["escalation_flag"] | (t["reopened_count"] > 0))  # noqa: E712
    step("Contradictory FCR flagged", "BR-RULE-09", contra.sum())
    t["is_fcr_contradictory"] = contra

    srt = t[t["subcategory"].notna()].sort_values(["created_at", "ticket_id"])
    gap = srt.groupby(["source_customer_id", "subcategory", "priority"])["created_at"].diff()
    dup_ids = set(srt.loc[gap <= pd.Timedelta(minutes=15), "ticket_id"])
    t["is_possible_duplicate"] = t["ticket_id"].isin(dup_ids)
    step("Near-duplicates flagged (excluded from KPIs)", "BR-RULE-01", len(dup_ids))

    for col, rule in [("root_cause", "M02"), ("knowledge_base_used", "M03"), ("channel", "M04"),
                      ("subcategory", "M05")]:
        m = t[col].isna() & (done if col == "root_cause" else True)
        step(f"Missing {col} kept as NULL", rule, m.sum())

    t["is_resolved"] = done
    t["is_open"] = t["ticket_status"].isin(OPEN)
    sr = cat.set_index("subcategory")["is_service_request"]
    is_sr = t["subcategory"].map(sr)
    t["is_incident"] = np.where(is_sr.notna(), ~is_sr.fillna(False).astype(bool),
                                t["root_cause"] != "Service Request")
    return t, pd.DataFrame(log)


def kpi_population(t: pd.DataFrame) -> pd.DataFrame:
    """Apply the KPI populations (same as analytics.fact_tickets)."""
    f = t[~t["is_possible_duplicate"]].copy()
    f["in_sla_population"] = f["is_resolved"] & ~f["is_invalid_timestamp"] & f["sla_target_hours"].notna()
    f["sla_breached"] = np.where(f["in_sla_population"], f["resolution_time_hours"] > f["sla_target_hours"], np.nan)
    f["in_duration_population"] = f["in_sla_population"] & ~f["is_resolution_outlier"]
    return f
