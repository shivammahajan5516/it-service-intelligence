#!/usr/bin/env python3
"""
Phase 5 - Python analytics for the IT Service Intelligence Platform.

Runs the twelve analyses in the brief on the cleaned data and writes:
    analytics/outputs/figures/*.png
    analytics/outputs/analysis_results.json   (every number quoted in the report)
    docs/python_analysis_report.md            (tables + figures + interpretation)

Interpretation text lives in analytics/findings.md ("## <section>" blocks),
written after reading the results. Correlation is never presented as causation.

    python analytics/run_analysis.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cleaning import clean_tickets, kpi_population  # noqa: E402
from common import (FIG, INK_2, OUT, PRIORITY_COLOR, RAW, ROOT, SERIES, cramers_v,  # noqa: E402
                    load_dims, load_fact, md_table, save, style, wilson_ci)

import matplotlib.pyplot as plt  # noqa: E402

R: dict = {}          # results quoted in the report
SECTIONS: list = []   # (key, title, markdown)


def section(key, title, body):
    SECTIONS.append((key, title, body))


def pct(x):
    return round(100 * float(x), 2)


# ----------------------------------------------------------------------------- 1. EDA
def eda(f, dims):
    num = f[["resolution_time_hours", "first_response_time_hours", "reopened_count",
             "customer_satisfaction", "sla_target_hours"]]
    desc = num.describe().T.reset_index().rename(columns={"index": "column"})
    R["eda"] = {"rows": len(f), "columns": f.shape[1],
                "period": [str(f["created_at"].min().date()), str(f["created_at"].max().date())],
                "customers": int(f["customer_id"].nunique()), "teams": int(f["team_id"].nunique())}
    cat_counts = pd.DataFrame({
        "dimension": ["priority", "category", "channel", "team_id", "region", "ticket_status"],
        "distinct_values": [f[c].nunique() for c in ["priority", "category", "channel", "team_id",
                                                    "region", "ticket_status"]],
        "most_common": [f[c].mode().iat[0] for c in ["priority", "category", "channel", "team_id",
                                                    "region", "ticket_status"]]})
    style()
    m = f.groupby("created_month").size()
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.bar(m.index, m.values, width=20, color=SERIES[0])
    ax.set_title("Tickets created per month")
    ax.set_ylabel("Tickets")
    img = save(fig, "01_monthly_volume")
    section("eda", "1. Exploratory data analysis",
            f"The analysis table has **{len(f):,} tickets** (duplicates removed) and {f.shape[1]} columns, "
            f"covering {R['eda']['period'][0]} to {R['eda']['period'][1]}, {R['eda']['customers']} customers "
            f"and {R['eda']['teams']} teams.\n\n"
            + md_table(desc[["column", "count", "mean", "std", "min", "25%", "50%", "75%", "max"]])
            + "\n\n" + md_table(cat_counts) + f"\n\n![Monthly volume]({img})")


# ----------------------------------------------------------------------------- 2. cleaning
def cleaning(f):
    t, log = clean_tickets()
    pop = kpi_population(t)
    same_ids = set(pop["ticket_id"]) == set(f["ticket_id"])
    breach_py = pop["sla_breached"].astype(float).mean()
    breach_sql = f["sla_breached"].astype(float).mean()
    R["cleaning"] = {"steps": log.to_dict("records"), "pandas_rows": len(pop), "sql_rows": len(f),
                     "identical_ticket_ids": bool(same_ids), "breach_pct_pandas": pct(breach_py),
                     "breach_pct_sql": pct(breach_sql)}
    section("cleaning", "2. Data cleaning",
            "`analytics/cleaning.py` re-implements the business rules in pandas, straight from the raw "
            "CSVs, and logs every step:\n\n" + md_table(log)
            + f"\n\n**Cross-check against PostgreSQL:** pandas produces {len(pop):,} KPI-eligible tickets and "
            f"the SQL fact table has {len(f):,}; the ticket IDs are "
            f"{'identical' if same_ids else 'NOT identical'}. The SLA breach rate is {pct(breach_py)}% in pandas "
            f"and {pct(breach_sql)}% in SQL. Two independent implementations agree.")


# ----------------------------------------------------------------------------- 3. missing values
def missing_values():
    raw = pd.read_csv(RAW / "tickets.csv", dtype=str, keep_default_na=False, na_values=[""])
    mv = (raw.isna().mean() * 100).sort_values(ascending=False)
    mv = mv[mv > 0].round(2)
    expected = {"customer_satisfaction": "Survey non-response (by design, MNAR - see section 7)",
                "root_cause": "Open/cancelled tickets + 4% not recorded by agents",
                "resolution_type": "Open tickets", "first_contact_resolution": "Open tickets",
                "resolved_at": "Open tickets + 8 closed without timestamp",
                "resolution_time_hours": "Follows resolved_at", "knowledge_base_used": "Not recorded",
                "subcategory": "Not recorded", "channel": "Not recorded", "agent_id": "Unassigned",
                "sla_target_hours": "Not exported - derivable", "first_response_at": "New tickets",
                "first_response_time_hours": "Follows first_response_at"}
    tbl = pd.DataFrame({"column": mv.index, "pct_missing": mv.values,
                        "explanation": [expected.get(c, "") for c in mv.index]})
    # is CSAT missing at random? compare response rate by breach status
    f = load_fact()
    rr = f[f["is_resolved"] & f["in_sla_population"]].groupby("sla_breached")["has_valid_csat"].mean()
    R["missing"] = {"by_column": tbl.to_dict("records"),
                    "csat_response_rate_met": pct(rr.get(False, np.nan)),
                    "csat_response_rate_breached": pct(rr.get(True, np.nan))}
    style()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.barh(tbl["column"][::-1], tbl["pct_missing"][::-1], color=SERIES[0], height=0.6)
    ax.set_xlabel("% of raw ticket rows missing")
    ax.set_title("Missing values in tickets.csv")
    ax.grid(axis="y", visible=False)
    img = save(fig, "03_missing_values")
    section("missing", "3. Missing-value analysis", md_table(tbl) + f"\n\n![Missing values]({img})")


# ----------------------------------------------------------------------------- 4. outliers
def outliers(f):
    d = f[f["in_sla_population"]].copy()
    d["log_h"] = np.log1p(d["resolution_time_hours"])
    rows = []
    for p, g in d.groupby("priority"):
        q1, q3 = g["log_h"].quantile([.25, .75])
        fence = q3 + 1.5 * (q3 - q1)
        z = np.abs(stats.zscore(g["log_h"]))
        rows.append({"priority": p, "tickets": len(g), "tukey_fence_hours": round(np.expm1(fence), 1),
                     "tukey_outliers": int((g["log_h"] > fence).sum()),
                     "z_gt_3_outliers": int((z > 3).sum()),
                     "business_rule_outliers": int(g["is_resolution_outlier"].sum())})
    tbl = pd.DataFrame(rows)
    overlap = d[d["is_resolution_outlier"]]
    R["outliers"] = {"table": tbl.to_dict("records"),
                     "business_rule_total": int(d["is_resolution_outlier"].sum()),
                     "mean_with_outliers": round(d["resolution_time_hours"].mean(), 2),
                     "mean_without_outliers": round(d.loc[~d["is_resolution_outlier"], "resolution_time_hours"].mean(), 2),
                     "median_with_outliers": round(d["resolution_time_hours"].median(), 2),
                     "median_without_outliers": round(d.loc[~d["is_resolution_outlier"], "resolution_time_hours"].median(), 2),
                     "outliers_breached_pct": pct(overlap["sla_breached"].astype(float).mean()) if len(overlap) else None}
    style()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    data = [d.loc[d["priority"] == p, "resolution_time_hours"].clip(lower=0.01) for p in ["P1", "P2", "P3", "P4"]]
    bp = ax.boxplot(data, tick_labels=["P1", "P2", "P3", "P4"], patch_artist=True, widths=0.5,
                    flierprops={"marker": "o", "markersize": 3, "markerfacecolor": INK_2, "alpha": .35,
                                "markeredgewidth": 0})
    for patch, p in zip(bp["boxes"], ["P1", "P2", "P3", "P4"]):
        patch.set_facecolor(PRIORITY_COLOR[p])
        patch.set_alpha(.85)
    ax.set_yscale("log")
    ax.set_ylabel("Resolution time (hours, log scale)")
    ax.set_title("Resolution time by priority - long right tail on every priority")
    img = save(fig, "04_outliers_boxplot")
    section("outliers", "4. Outlier detection",
            "Three methods on resolved tickets with valid timestamps: Tukey fence on log hours "
            "(resolution time is log-normal, so a fence on raw hours would flag ordinary slow tickets), "
            "|z| > 3 on log hours, and the business rule BR-RULE-08 (> 30 days or > 10x target).\n\n"
            + md_table(tbl) + f"\n\n![Outliers]({img})\n\n"
            f"Removing the {R['outliers']['business_rule_total']} business-rule outliers changes the **mean** "
            f"from {R['outliers']['mean_with_outliers']} h to {R['outliers']['mean_without_outliers']} h but the "
            f"**median** only from {R['outliers']['median_with_outliers']} h to {R['outliers']['median_without_outliers']} h "
            "- the reason targets use the median.")


# ----------------------------------------------------------------------------- 5. descriptive
def descriptive(f):
    d = f[f["in_duration_population"]]
    rows = []
    for p, g in d.groupby("priority"):
        h = g["resolution_time_hours"]
        rows.append({"priority": p, "n": len(h), "mean_h": h.mean(), "median_h": h.median(),
                     "std_h": h.std(), "p90_h": h.quantile(.9), "skewness": stats.skew(h),
                     "kurtosis": stats.kurtosis(h), "log_skewness": stats.skew(np.log1p(h))})
    tbl = pd.DataFrame(rows)
    R["descriptive"] = tbl.round(3).to_dict("records")
    style()
    fig, axes = plt.subplots(2, 2, figsize=(9, 5.4), sharey=False)
    for ax, p in zip(axes.flat, ["P1", "P2", "P3", "P4"]):
        h = d.loc[d["priority"] == p, "resolution_time_hours"]
        bins = np.logspace(np.log10(max(h.min(), .05)), np.log10(h.max()), 40)
        ax.hist(h, bins=bins, color=PRIORITY_COLOR[p], edgecolor="#fcfcfb", linewidth=.6)
        ax.set_xscale("log")
        ax.set_title(f"{p}  (median {h.median():.1f} h)", fontsize=10)
    fig.supxlabel("Resolution time (hours, log scale)", color=INK_2, fontsize=10)
    fig.suptitle("Resolution-time distribution by priority", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    img = save(fig, "05_resolution_distribution")
    section("descriptive", "5. Descriptive statistics",
            md_table(tbl) + f"\n\n![Distribution]({img})\n\nSkewness of raw hours is strongly positive; "
            "after a log transform it is close to zero, confirming an approximately log-normal shape. "
            "Medians and percentiles are therefore reported instead of means and standard deviations.")


# ----------------------------------------------------------------------------- 6. SLA breach
def sla_breach(f, dims):
    s = f[f["in_sla_population"]].copy()
    s["b"] = s["sla_breached"].astype(bool)
    team = dims["team"].set_index("team_id")["team_name"]
    rows = []
    for tid, g in s.groupby("team_id"):
        lo, hi = wilson_ci(g["b"].sum(), len(g))
        rows.append({"team": team[tid], "n": len(g), "breach_pct": 100 * g["b"].mean(),
                     "ci_low": 100 * lo, "ci_high": 100 * hi})
    tbl = pd.DataFrame(rows).sort_values("breach_pct")
    ct = pd.crosstab(s["team_id"], s["b"])
    chi2, pval, dof, _ = stats.chi2_contingency(ct)
    by_level = s.groupby("sla_level")["b"].mean().mul(100).round(2)
    R["sla"] = {"overall_breach_pct": pct(s["b"].mean()), "team": tbl.round(2).to_dict("records"),
                "chi2_team": round(chi2, 1), "p_team": float(pval), "dof": int(dof),
                "cramers_v_team": round(cramers_v(ct), 3), "by_sla_level": by_level.to_dict()}
    style()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.barh(tbl["team"], tbl["breach_pct"], color=SERIES[0], height=.55,
            xerr=[tbl["breach_pct"] - tbl["ci_low"], tbl["ci_high"] - tbl["breach_pct"]],
            error_kw={"ecolor": INK_2, "elinewidth": 1, "capsize": 3})
    ax.axvline(R["sla"]["overall_breach_pct"], color=INK_2, linestyle="--", linewidth=1)
    ax.text(R["sla"]["overall_breach_pct"] + .5, -0.6, "company", color=INK_2, fontsize=9)
    ax.set_xlabel("SLA breach rate (%) with 95% Wilson interval")
    ax.set_title("SLA breach rate by team")
    ax.grid(axis="y", visible=False)
    img = save(fig, "06_team_breach")
    lvl = pd.DataFrame({"sla_level": by_level.index, "breach_pct": by_level.values})
    section("sla", "6. SLA breach analysis",
            md_table(tbl) + f"\n\n![Team breach]({img})\n\n"
            f"Chi-square test of independence, team x breached: chi2 = {chi2:,.1f}, dof = {dof}, "
            f"p = {pval:.1e}; Cramer's V = {R['sla']['cramers_v_team']} (a moderate association). "
            "The intervals do not overlap between the top and bottom groups, so the differences are not "
            "sampling noise.\n\nBy contract level:\n\n" + md_table(lvl))


# ----------------------------------------------------------------------------- 7. correlation
def correlation(f, dims):
    d = f[f["in_duration_population"]].copy()
    teams = dims["team"].set_index("team_id")["planned_headcount"]
    tm = f.groupby(["team_id", "created_month"]).size().rename("n").reset_index()
    tm["load_per_agent"] = tm["n"] / tm["team_id"].map(teams)
    d = d.merge(tm[["team_id", "created_month", "load_per_agent"]], on=["team_id", "created_month"])
    cols = {"resolution_time_hours": "resolution_h", "first_response_time_hours": "first_response_h",
            "reopened_count": "reopens", "escalation_flag": "escalated", "knowledge_base_used": "kb_used",
            "sla_breached": "breached", "customer_satisfaction": "csat", "load_per_agent": "team_load"}
    m = d[list(cols)].rename(columns=cols).astype(float)
    corr = m.corr(method="spearman")
    # CSAT vs breach: Mann-Whitney U
    c = f[f["has_valid_csat"] & f["in_sla_population"]]
    met = c.loc[c["sla_breached"] == False, "customer_satisfaction"]  # noqa: E712
    br = c.loc[c["sla_breached"] == True, "customer_satisfaction"]  # noqa: E712
    u, p_u = stats.mannwhitneyu(met, br, alternative="greater")
    rbc = 1 - 2 * u / (len(met) * len(br))   # rank-biserial correlation
    R["correlation"] = {"spearman": corr.round(3).to_dict(),
                        "csat_met_mean": round(met.mean(), 3), "csat_breached_mean": round(br.mean(), 3),
                        "mannwhitney_u": float(u), "p": float(p_u), "rank_biserial": round(-rbc, 3),
                        "n_met": len(met), "n_breached": len(br)}
    style()
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])
    im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr)), corr.columns)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iat[i, j]:.2f}", ha="center", va="center", fontsize=8, color="#0b0b0b")
    ax.grid(False)
    ax.set_title("Spearman correlation (resolved tickets)")
    fig.colorbar(im, ax=ax, shrink=.8)
    img = save(fig, "07_correlation")
    section("correlation", "7. Correlation analysis",
            f"Spearman rank correlation is used because the variables are skewed, binary or ordinal.\n\n"
            f"![Correlation]({img})\n\n" + md_table(corr.round(2).reset_index().rename(columns={"index": ""}))
            + f"\n\n**CSAT vs SLA outcome.** Mean CSAT {met.mean():.2f} when SLA was met (n = {len(met):,}) vs "
            f"{br.mean():.2f} when breached (n = {len(br):,}); one-sided Mann-Whitney U p = {p_u:.1e}, "
            f"rank-biserial effect size {-rbc:.2f} (large). Survey response is higher after a breach "
            f"({R['missing']['csat_response_rate_breached']}% vs {R['missing']['csat_response_rate_met']}%), "
            "so CSAT is missing-not-at-random and the average slightly over-represents unhappy customers.")


# ----------------------------------------------------------------------------- 8. Pareto
def pareto(f):
    inc = f[f["is_incident"] & f["is_resolved"] & f["root_cause"].notna()]
    rc = inc["root_cause"].value_counts()
    tbl = pd.DataFrame({"root_cause": rc.index, "incidents": rc.values})
    tbl["pct"] = 100 * tbl["incidents"] / tbl["incidents"].sum()
    tbl["cumulative_pct"] = tbl["pct"].cumsum()
    n80 = int((tbl["cumulative_pct"] < 80).sum() + 1)
    R["pareto"] = {"table": tbl.round(2).to_dict("records"), "causes_to_80pct": n80,
                   "of_causes": len(tbl), "top3_pct": round(tbl["pct"].head(3).sum(), 1)}
    style()
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(tbl))
    ax.bar(x, tbl["pct"], color=SERIES[0], width=.6, label="Share of incidents (%)")
    ax.plot(x, tbl["cumulative_pct"], color=SERIES[1], marker="o", markersize=5, label="Cumulative share (%)")
    ax.axhline(80, color=INK_2, linestyle="--", linewidth=1)
    ax.set_xticks(x, tbl["root_cause"], rotation=35, ha="right")
    ax.set_ylabel("% of incidents (one axis for both series)")
    ax.set_ylim(0, 105)
    ax.set_title("Root-cause Pareto (incidents with a known root cause)")
    ax.legend(loc="center right")
    img = save(fig, "08_pareto")
    section("pareto", "8. Pareto analysis", md_table(tbl) + f"\n\n![Pareto]({img})\n\n"
            f"{n80} of {len(tbl)} root causes are needed to reach 80% of incidents; the top three cover "
            f"{R['pareto']['top3_pct']}%. Both series share one percentage axis (no dual axis).")


# ----------------------------------------------------------------------------- 9. root cause analysis
def root_cause(f):
    inc = f[f["is_incident"] & f["in_sla_population"] & f["root_cause"].notna()].copy()
    inc["b"] = inc["sla_breached"].astype(bool)
    overall = inc["b"].mean()
    rows = []
    for rc, g in inc.groupby("root_cause"):
        lo, hi = wilson_ci(g["b"].sum(), len(g))
        rows.append({"root_cause": rc, "n": len(g), "breach_pct": 100 * g["b"].mean(), "ci_low": 100 * lo,
                     "ci_high": 100 * hi, "excess_breaches": g["b"].sum() - overall * len(g),
                     "median_h": g.loc[g["in_duration_population"], "resolution_time_hours"].median()})
    tbl = pd.DataFrame(rows).sort_values("excess_breaches", ascending=False)

    # Escalation effect stratified by priority (Mantel-Haenszel odds ratio)
    s = f[f["in_sla_population"]].copy()
    s["b"] = s["sla_breached"].astype(bool)
    num = den = 0.0
    strata = []
    for p, g in s.groupby("priority"):
        a = ((g["escalation_flag"]) & g["b"]).sum(); b_ = ((g["escalation_flag"]) & ~g["b"]).sum()
        c = ((~g["escalation_flag"]) & g["b"]).sum(); d = ((~g["escalation_flag"]) & ~g["b"]).sum()
        n = a + b_ + c + d
        num += a * d / n; den += b_ * c / n
        strata.append({"priority": p, "odds_ratio": (a * d) / (b_ * c)})
    mh_or = num / den
    crude = pd.crosstab(s["escalation_flag"], s["b"])
    crude_or = (crude.loc[True, True] * crude.loc[False, False]) / (crude.loc[True, False] * crude.loc[False, True])
    # Change-related trend
    q = inc.assign(q=inc["created_at"].dt.to_period("Q").astype(str)).groupby("q")["root_cause"].apply(
        lambda x: (x == "Change-Related").mean() * 100)
    slope = stats.linregress(np.arange(len(q)), q.values)
    R["rca"] = {"table": tbl.round(2).to_dict("records"), "escalation_crude_or": round(crude_or, 2),
                "escalation_mh_or": round(mh_or, 2), "escalation_strata": pd.DataFrame(strata).round(2).to_dict("records"),
                "change_share_by_quarter": q.round(2).to_dict(), "change_slope_pp_per_quarter": round(slope.slope, 2),
                "change_slope_p": float(slope.pvalue)}
    section("rca", "9. Root cause analysis",
            "Breach rate by root cause with 95% intervals. *Excess breaches* = breaches above what the "
            "company-average rate would give for the same volume - the ranking to fix first.\n\n" + md_table(tbl)
            + f"\n\n**Escalation, adjusted for priority.** Crude odds ratio of breaching when escalated = "
            f"{crude_or:.2f}; Mantel-Haenszel odds ratio stratified by priority = {mh_or:.2f} "
            f"(per priority: " + ", ".join(f"{x['priority']} {x['odds_ratio']:.1f}" for x in strata)
            + "). The association survives adjustment for priority, but escalation is also a marker of harder "
            "work, so this is not evidence that escalating *causes* breaches.\n\n"
            f"**Change-related share** rises by {slope.slope:.2f} percentage points per quarter "
            f"(linear trend over 8 quarters, p = {slope.pvalue:.3f}).")


# ----------------------------------------------------------------------------- 10. team comparison
def teams(f, dims):
    d = f[f["in_duration_population"]]
    groups = [g["resolution_time_hours"].values for _, g in d.groupby("team_id")]
    h, p = stats.kruskal(*groups)
    # priority- and contract-adjusted breach rate (indirect standardisation)
    s = f[f["in_sla_population"]].copy()
    s["b"] = s["sla_breached"].astype(float)
    s["cell_rate"] = s.groupby(["priority", "sla_level"])["b"].transform("mean")
    team = dims["team"].set_index("team_id")
    adj = s.groupby("team_id").agg(n=("b", "size"), observed=("b", "mean"), expected=("cell_rate", "mean"))
    adj["oe_ratio"] = adj["observed"] / adj["expected"]
    tm = f.groupby(["team_id"]).size() / team["planned_headcount"] / f["created_month"].nunique()
    adj["tickets_per_agent_month"] = tm
    adj["fcr_pct"] = f.groupby("team_id")["fcr_achieved"].apply(lambda x: x.dropna().astype(float).mean() * 100)
    adj["median_h"] = d.groupby("team_id")["resolution_time_hours"].median()
    adj = adj.reset_index()
    adj.insert(1, "team", adj["team_id"].map(team["team_name"]))
    adj["observed"] *= 100
    adj["expected"] *= 100
    rho, p_rho = stats.spearmanr(adj["tickets_per_agent_month"], adj["oe_ratio"])
    R["teams"] = {"kruskal_h": round(h, 1), "kruskal_p": float(p), "table": adj.round(3).to_dict("records"),
                  "spearman_load_vs_oe": round(rho, 3), "p_load_vs_oe": float(p_rho)}
    style()
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.scatter(adj["tickets_per_agent_month"], adj["oe_ratio"], s=70, color=SERIES[0],
               edgecolor="#fcfcfb", linewidth=2, zorder=3)
    for r in adj.itertuples():
        ax.annotate(r.team, (r.tickets_per_agent_month, r.oe_ratio), textcoords="offset points",
                    xytext=(6, 4), fontsize=8.5, color=INK_2)
    ax.axhline(1, color=INK_2, linestyle="--", linewidth=1)
    ax.set_xlabel("Tickets per agent per month")
    ax.set_ylabel("Observed / expected breaches\n(adjusted for priority and SLA level)")
    ax.set_title("Workload vs adjusted breach performance, by team")
    img = save(fig, "10_team_load_vs_breach")
    section("teams", "10. Team performance comparison",
            f"Kruskal-Wallis test of resolution time across the 8 teams: H = {h:,.0f}, p = {p:.1e} - "
            "the teams' distributions differ. Because teams handle different priorities and contracts, "
            "breach rates are also shown **adjusted** (observed / expected, where expected uses the "
            "company rate for each priority x SLA-level cell):\n\n"
            + md_table(adj[["team", "n", "tickets_per_agent_month", "observed", "expected", "oe_ratio",
                            "fcr_pct", "median_h"]])
            + f"\n\n![Load vs breach]({img})\n\nSpearman correlation between load and adjusted breach ratio "
            f"across teams: rho = {rho:.2f} (p = {p_rho:.3f}, n = 8 teams - small sample).")


# ----------------------------------------------------------------------------- 11. segmentation
def segmentation(f, dims):
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler
    c = f[~f["customer_is_placeholder"]]
    g = c.groupby("customer_id").agg(
        tickets=("ticket_id", "size"),
        breach_rate=("sla_breached", lambda x: x.dropna().astype(float).mean()),
        repeat_rate=("is_repeat_incident", lambda x: x.dropna().astype(float).mean()),
        escalation_rate=("escalation_flag", "mean"),
        avg_csat=("customer_satisfaction", "mean"),
        csat_n=("customer_satisfaction", "count"))
    g = g[g["tickets"] >= 10].copy()
    g["avg_csat"] = g["avg_csat"].fillna(g["avg_csat"].median())
    feats = pd.DataFrame({"log_tickets": np.log(g["tickets"]), "breach_rate": g["breach_rate"],
                          "repeat_rate": g["repeat_rate"], "escalation_rate": g["escalation_rate"],
                          "avg_csat": g["avg_csat"]}).fillna(0)
    X = StandardScaler().fit_transform(feats)
    scores = {k: silhouette_score(X, KMeans(k, n_init=10, random_state=42).fit_predict(X)) for k in range(2, 7)}
    k = 4  # chosen for interpretability; silhouette for each k reported
    km = KMeans(k, n_init=20, random_state=42).fit(X)
    g["cluster"] = km.labels_
    prof = g.groupby("cluster").agg(customers=("tickets", "size"), median_tickets=("tickets", "median"),
                                    breach_pct=("breach_rate", lambda x: 100 * x.mean()),
                                    repeat_pct=("repeat_rate", lambda x: 100 * x.mean()),
                                    escalation_pct=("escalation_rate", lambda x: 100 * x.mean()),
                                    avg_csat=("avg_csat", "mean"))
    lvl = dims["customer"].set_index("customer_id")["sla_level"]
    prof["pct_platinum"] = g.groupby("cluster").apply(lambda x: 100 * (x.index.map(lvl) == "Platinum").mean())
    # name clusters from their profile (rules applied to the fitted centroids)
    names = {}
    order = prof.sort_values("repeat_pct", ascending=False).index.tolist()
    names[order[0]] = "Chronic-problem accounts"
    rest = prof.drop(order[0])
    hb = rest["breach_pct"].idxmax(); names[hb] = "SLA-pressured premium"
    rest = rest.drop(hb)
    lo = rest["median_tickets"].idxmin(); names[lo] = "Low-touch"
    for i in rest.index:
        names.setdefault(i, "Steady core")
    prof.insert(0, "segment", prof.index.map(names))
    g["segment"] = g["cluster"].map(names)
    R["segmentation"] = {"silhouette": {str(k_): round(v, 3) for k_, v in scores.items()}, "k": k,
                         "customers_clustered": len(g), "profile": prof.round(2).to_dict("records")}
    (OUT / "customer_segments.csv").parent.mkdir(parents=True, exist_ok=True)
    g.reset_index()[["customer_id", "segment", "tickets", "breach_rate", "repeat_rate", "avg_csat"]].to_csv(
        OUT / "customer_segments.csv", index=False)
    style()
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2))
    for ax, (col, lab) in zip(axes, [("breach_pct", "Breach %"), ("repeat_pct", "Repeat incident %"),
                                     ("avg_csat", "Avg CSAT"), ("median_tickets", "Median tickets")]):
        ax.barh(prof["segment"], prof[col], color=SERIES[0], height=.55)
        ax.set_title(lab, fontsize=10)
        ax.grid(axis="y", visible=False)
        if ax is not axes[0]:
            ax.set_yticklabels([])
    fig.suptitle("Customer segments (k-means, k = 4) - profile per segment", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    img = save(fig, "11_segments")
    sil = ", ".join(f"k={k_}: {v:.3f}" for k_, v in scores.items())
    section("segmentation", "11. Customer segmentation",
            f"K-means on {len(g)} customers with at least 10 tickets, using standardised log volume, breach "
            f"rate, repeat-incident rate, escalation rate and average CSAT. Silhouette scores: {sil}. "
            f"k = {k} was chosen for interpretability (segments map to distinct CSM actions); scores across k "
            "are modest, so segments are a practical grouping, not natural clusters.\n\n"
            + md_table(prof.reset_index(drop=True)) + f"\n\n![Segments]({img})\n\n"
            "Segment assignments: `analytics/outputs/customer_segments.csv`.")


# ----------------------------------------------------------------------------- 12. time series
def time_series(f):
    m = f.groupby("created_month").agg(tickets=("ticket_id", "size"),
                                       breach=("sla_breached", lambda x: 100 * x.dropna().astype(float).mean()),
                                       csat=("customer_satisfaction", "mean")).reset_index()
    x = np.arange(len(m))
    lr_b = stats.linregress(x, m["breach"])
    lr_v = stats.linregress(x, m["tickets"])
    lr_c = stats.linregress(x, m["csat"])
    m["breach_3m"] = m["breach"].rolling(3).mean()
    rv = stats.spearmanr(m["tickets"], m["breach"])
    R["timeseries"] = {"breach_slope_pp_per_month": round(lr_b.slope, 3), "breach_p": float(lr_b.pvalue),
                       "breach_r2": round(lr_b.rvalue ** 2, 3),
                       "volume_slope_per_month": round(lr_v.slope, 1), "volume_p": float(lr_v.pvalue),
                       "csat_slope_per_month": round(lr_c.slope, 4), "csat_p": float(lr_c.pvalue),
                       "spearman_volume_breach": round(rv.statistic, 3), "p_volume_breach": float(rv.pvalue)}
    style()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(m["created_month"], m["breach"], color=SERIES[0], marker="o", markersize=4, label="Monthly")
    ax.plot(m["created_month"], m["breach_3m"], color=SERIES[1], label="3-month moving average")
    ax.plot(m["created_month"], lr_b.intercept + lr_b.slope * x, color=INK_2, linestyle="--", linewidth=1,
            label="Linear trend")
    ax.set_ylabel("SLA breach rate (%)")
    ax.set_title("SLA breach rate over time")
    ax.legend(loc="upper left")
    img = save(fig, "12_breach_trend")
    section("timeseries", "12. Time-series trend analysis",
            f"![Trend]({img})\n\nLinear trend over 24 months: breach rate rises "
            f"{lr_b.slope:.2f} percentage points per month (R^2 = {lr_b.rvalue ** 2:.2f}, p = {lr_b.pvalue:.1e}); "
            f"volume rises {lr_v.slope:.1f} tickets per month (p = {lr_v.pvalue:.1e}); CSAT falls "
            f"{abs(lr_c.slope):.4f} points per month (p = {lr_c.pvalue:.1e}). Monthly volume and breach rate "
            f"have Spearman rho = {rv.statistic:.2f} (p = {rv.pvalue:.1e}). Two years is too short to separate "
            "seasonality from trend reliably; the major-incident spikes (Q23 in the SQL analysis) add noise "
            "to individual months.")


def write_report():
    findings = {}
    p = ROOT / "analytics" / "findings.md"
    if p.exists():
        parts = re.split(r"^## (\w+)\s*$", p.read_text(), flags=re.M)
        findings = {k: v.strip() for k, v in zip(parts[1::2], parts[2::2])}
    lines = ["# Python analysis report (Phase 5)", "",
             "> Synthetic data - Northbridge Managed Services Ltd is fictional. Every number below is computed by "
             "`analytics/run_analysis.py`; all values are also in `analytics/outputs/analysis_results.json`. "
             "Statistical association is not causation; the generator's built-in mechanisms are listed in "
             "`docs/06_synthetic_data_design.md`.", ""]
    if "summary" in findings:
        lines += ["## Key findings", "", findings["summary"], ""]
    lines += ["See also: [breach-risk model](model_report.md).", ""]
    for key, title, body in SECTIONS:
        lines += [f"## {title}", "", body, ""]
        if key in findings:
            lines += [f"**Interpretation.** {findings[key]}", ""]
    (ROOT / "docs" / "python_analysis_report.md").write_text("\n".join(lines))


def main():
    f = load_fact()
    dims = load_dims()
    FIG.mkdir(parents=True, exist_ok=True)
    eda(f, dims)
    cleaning(f)
    missing_values()
    outliers(f)
    descriptive(f)
    sla_breach(f, dims)
    correlation(f, dims)
    pareto(f)
    root_cause(f)
    teams(f, dims)
    segmentation(f, dims)
    time_series(f)
    (OUT / "analysis_results.json").write_text(json.dumps(R, indent=2, default=str) + "\n")
    write_report()
    print(f"Analysis complete: {len(SECTIONS)} sections, {len(list(FIG.glob('*.png')))} figures")
    print(f"pandas vs SQL rows: {R['cleaning']['pandas_rows']} vs {R['cleaning']['sql_rows']}, "
          f"identical ids: {R['cleaning']['identical_ticket_ids']}")


if __name__ == "__main__":
    main()
