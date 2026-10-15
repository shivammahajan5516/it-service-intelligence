#!/usr/bin/env python3
"""
Acceptance values for the Power BI model.

Re-implements the key DAX measures in pandas over data/processed/pbi_fact_tickets.csv
(the same table Power BI imports), so you can check your report shows the same
numbers. Writes powerbi/expected_values.md.

    python powerbi/expected_values.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def measures(f: pd.DataFrame, headcount: float, months: int) -> dict:
    sla = f[f["in_sla_population"] == 1]
    dur = f.loc[f["in_duration_population"] == 1, "resolution_time_hours"]
    res = f[f["is_resolved"] == 1]
    rep = f["is_repeat_incident"].dropna()
    return {
        "Total Tickets": len(f),
        "Open Tickets": int((f["is_open"] == 1).sum()),
        "SLA Breach %": 100 * (f["sla_breached"] == 1).sum() / len(sla) if len(sla) else np.nan,
        "SLA Compliance %": 100 - 100 * (f["sla_breached"] == 1).sum() / len(sla) if len(sla) else np.nan,
        "Avg Resolution Hours": dur.mean(),
        "Median Resolution Hours": dur.median(),
        "P90 Resolution Hours": dur.quantile(0.9),       # = PERCENTILE.INC
        "FCR %": 100 * (f["fcr_achieved"] == 1).sum() / (f["in_fcr_population"] == 1).sum(),
        "Reopen %": 100 * (res["is_reopened"] == 1).mean(),
        "Escalation %": 100 * (f["is_escalated"] == 1).mean(),
        "Avg CSAT": f["customer_satisfaction"].mean(),
        "CSAT Responses": int(f["customer_satisfaction"].count()),
        "Repeat Incident %": 100 * (rep == 1).mean(),
        "Tickets per Agent per Month": len(f) / headcount / months,
    }


def main():
    f = pd.read_csv(ROOT / "data" / "processed" / "pbi_fact_tickets.csv", parse_dates=["created_date"])
    teams = pd.read_csv(ROOT / "data" / "processed" / "dim_team.csv")
    hc = teams.set_index("team_id")["planned_headcount"]
    overall = measures(f, hc.sum(), f["created_month"].nunique())
    rows = [{"Context": "All data", "Measure": k, "Expected": v} for k, v in overall.items()]
    for tid, g in f.groupby("team_id"):
        m = measures(g, hc[tid], f["created_month"].nunique())
        for k in ["Total Tickets", "SLA Breach %", "Median Resolution Hours", "FCR %", "Avg CSAT",
                  "Tickets per Agent per Month"]:
            rows.append({"Context": f"Team {tid} ({teams.set_index('team_id').loc[tid, 'team_name']})",
                         "Measure": k, "Expected": m[k]})
    for month in ["2024-12-01", "2025-12-01"]:
        g = f[f["created_month"] == month]
        m = measures(g, hc.sum(), 1)
        rows.append({"Context": f"Month {month[:7]}", "Measure": "SLA Breach %", "Expected": m["SLA Breach %"]})
        rows.append({"Context": f"Month {month[:7]}", "Measure": "Total Tickets", "Expected": m["Total Tickets"]})
    y24, y25 = f[f["created_date"].dt.year == 2024], f[f["created_date"].dt.year == 2025]
    rows.append({"Context": "Year 2025", "Measure": "Tickets YoY %", "Expected": 100 * (len(y25) - len(y24)) / len(y24)})
    for r in rows:
        v = r["Expected"]
        r["Expected"] = f"{v:,}" if isinstance(v, (int, np.integer)) else f"{float(v):,.2f}"
    out = pd.DataFrame(rows)
    lines = ["# Power BI acceptance values", "",
             "Computed by `powerbi/expected_values.py` from `data/processed/pbi_fact_tickets.csv`. Percentages are "
             "shown as numbers (18.15 = 18.15%). Your report must match these to the displayed precision.", "",
             "| Context | Measure | Expected |", "|---|---|---:|"]
    lines += [f"| {r.Context} | {r.Measure} | {r.Expected} |" for r in out.itertuples()]
    (ROOT / "powerbi" / "expected_values.md").write_text("\n".join(lines) + "\n")
    print(out.head(14).to_string(index=False))


if __name__ == "__main__":
    main()
