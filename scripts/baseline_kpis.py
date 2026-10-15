#!/usr/bin/env python3
"""
Preliminary baseline KPIs used to set the Phase 1 business objectives.

Applies a minimal, documented pre-clean (the full cleaning layer is built
in PostgreSQL in Phase 3):
  * drop exact duplicate rows and near-duplicates flagged by D03
  * exclude cancelled tickets
  * exclude tickets with invalid timestamps (T03/T04/T05) or business-rule outliers (O02)
  * CSAT outside 1-5 treated as missing
  * category labels normalised with a mapping table

Writes data/reports/baseline_kpis.json and prints a summary.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CAT_FIX = {
    "network": "Network", "NETWORK": "Network", "Network ": "Network", "Netwrk": "Network",
    "Access and Identity": "Access & Identity", "access & identity": "Access & Identity",
    "Access/Identity": "Access & Identity", "H/W": "Hardware", "hardware": "Hardware",
    "Hardware ": "Hardware", "Email and Collaboration": "Email & Collaboration",
    "E-mail & Collaboration": "Email & Collaboration", "software": "Software", "SW": "Software",
    "Infra": "Infrastructure", "infrastructure": "Infrastructure", "Cloud": "Cloud Services",
    "cloud services": "Cloud Services", "Business Apps": "Business Applications",
    "business applications": "Business Applications", "security": "Security",
    "Cyber Security": "Security", "DB": "Database", "database": "Database",
}


def main():
    raw, rep = ROOT / "data" / "raw", ROOT / "data" / "reports"
    t = pd.read_csv(raw / "tickets.csv", parse_dates=["created_at", "first_response_at", "resolved_at"])
    teams = pd.read_csv(raw / "support_teams.csv")
    exc = pd.read_csv(rep / "records_for_investigation.csv")
    dup = pd.read_csv(rep / "duplicate_report.csv")

    t = t.drop_duplicates()
    t = t[~t["ticket_id"].isin(dup.loc[dup["duplicate_type"] == "near_duplicate", "ticket_id"])]
    bad = exc.loc[exc["check_id"].isin(["T03", "T04", "T05", "O02", "T01"]), "ticket_id"]
    t = t[~t["ticket_id"].isin(bad) & (t["ticket_status"] != "Cancelled")].copy()
    t["category"] = t["category"].replace(CAT_FIX)
    t.loc[~t["customer_satisfaction"].between(1, 5), "customer_satisfaction"] = np.nan

    done = t[t["ticket_status"].isin(["Resolved", "Closed"])].copy()
    done["breached"] = done["resolution_time_hours"] > done["sla_target_hours"]
    done = done[done["sla_target_hours"].notna()]
    done["half"] = done["created_at"].dt.year.astype(str) + "-H" + np.where(done["created_at"].dt.month <= 6, "1", "2")

    def kpis(df):
        return {
            "tickets_resolved": int(len(df)),
            "sla_breach_rate_pct": round(100 * df["breached"].mean(), 1),
            "median_resolution_hours": round(df["resolution_time_hours"].median(), 1),
            "mean_resolution_hours": round(df["resolution_time_hours"].mean(), 1),
            "fcr_rate_pct": round(100 * (df["first_contact_resolution"] == True).mean(), 1),  # noqa: E712
            "reopen_rate_pct": round(100 * (df["reopened_count"] > 0).mean(), 1),
            "escalation_rate_pct": round(100 * (df["escalation_flag"] == True).mean(), 1),  # noqa: E712
            "avg_csat": round(df["customer_satisfaction"].mean(), 2),
            "csat_response_rate_pct": round(100 * df["customer_satisfaction"].notna().mean(), 1),
        }

    by_half = {h: kpis(g) for h, g in done.groupby("half")}
    overall = kpis(done)

    # repeat incidents: same customer + subcategory within 30 days of a previous ticket
    inc = done[done["root_cause"] != "Service Request"].sort_values("created_at")
    prev = inc.groupby(["customer_id", "subcategory"])["created_at"].shift()
    inc_repeat = ((inc["created_at"] - prev).dt.days <= 30)
    repeat_rate = round(100 * inc_repeat.mean(), 1)
    cust_rep = inc[inc_repeat].groupby("customer_id").size().sort_values(ascending=False)
    top30_share = round(100 * cust_rep.head(30).sum() / cust_rep.sum(), 1)

    # workload per agent per month (2025)
    y25 = t[t["created_at"].dt.year == 2025]
    per_agent = (y25.groupby("team_id").size() / 12 / teams.set_index("team_id")["planned_headcount"]).round(1)

    # root cause concentration (incidents only, root cause known)
    rc = inc["root_cause"].dropna().value_counts(normalize=True)
    top3 = round(100 * rc.head(3).sum(), 1)

    team_breach = done.groupby("team_id")["breached"].mean().mul(100).round(1)

    out = {
        "note": "Preliminary baseline from a minimal pre-clean of synthetic data; recomputed in Phase 4/5.",
        "overall": overall, "by_half_year": by_half,
        "repeat_incident_rate_pct": repeat_rate,
        "top30_customers_share_of_repeat_incidents_pct": top30_share,
        "tickets_per_agent_per_month_2025": per_agent.to_dict(),
        "team_sla_breach_rate_pct": team_breach.to_dict(),
        "root_cause_top3": rc.head(3).round(3).to_dict(), "root_cause_top3_share_pct": top3,
        "open_backlog_at_snapshot": int(t["ticket_status"].isin(["New", "In Progress", "Pending Customer", "On Hold"]).sum()),
    }
    (rep / "baseline_kpis.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
