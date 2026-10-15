#!/usr/bin/env python3
"""
SLA breach-risk model (Phase 5, optional predictive model).

Question: at the moment a ticket is LOGGED, how likely is it to breach SLA?

Leakage control - only information known at creation time is used:
  * ticket attributes chosen at logging: priority, category, subcategory complexity,
    channel, resolver team, SLA level / target, company size, hour, weekday, out-of-hours
  * history computed strictly from EARLIER tickets: team workload in the previous
    7 days, customer's prior ticket count and prior breach rate (only breaches already
    known - i.e. resolved - before this ticket was created)
  * EXCLUDED (known only later): resolution time, first response, escalation, reopens,
    FCR, root cause, resolution type, KB use, CSAT, status.

Split - chronological, never random:
  train  2024-01 .. 2025-03   (model fitting)
  valid  2025-04 .. 2025-06   (threshold selection, model choice)
  test   2025-07 .. 2025-12   (reported once, untouched until the end)

Outputs: analytics/outputs/model_metrics.json, figures, docs/model_report.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INK_2, OUT, ROOT, SERIES, load_dims, load_fact, md_table, save, style  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

CAT = ["priority", "category", "complexity_tier", "channel", "team_id", "sla_level", "company_size",
       "weekday"]
NUM = ["sla_target_hours", "hour", "is_out_of_hours", "team_load_7d", "cust_prior_tickets",
       "cust_prior_breach_rate", "cust_prior_resolved"]
SEED = 42


def build_features(f: pd.DataFrame, dims) -> pd.DataFrame:
    d = f.copy().sort_values(["created_at", "ticket_id"]).reset_index(drop=True)
    d = d.merge(dims["customer"][["customer_id", "company_size"]], on="customer_id", how="left")
    d["hour"] = d["created_at"].dt.hour
    d["weekday"] = d["created_at"].dt.day_name()
    d["is_out_of_hours"] = d["is_out_of_hours"].astype(float)
    d["channel"] = d["channel"].fillna("Unknown")
    d["complexity_tier"] = d["complexity_tier"].fillna("Unknown")

    # team workload: tickets logged for the same team in the 7 days BEFORE this ticket
    load = []
    for _, g in d.groupby("team_id", sort=False):
        s = pd.Series(1, index=g["created_at"])
        roll = s.rolling("7D", closed="left").sum().fillna(0).to_numpy()
        load.append(pd.Series(roll, index=g.index))
    d["team_load_7d"] = pd.concat(load)

    # customer history: prior tickets, and breaches already KNOWN (resolved before creation)
    d["cust_prior_tickets"] = d.groupby("customer_id").cumcount()
    known = d[d["in_sla_population"]][["customer_id", "resolved_at", "sla_breached"]].copy()
    known["b"] = known["sla_breached"].astype(float)
    known = known.sort_values("resolved_at")
    out_rate = np.full(len(d), np.nan)
    out_n = np.zeros(len(d))
    for cid, g in d.groupby("customer_id", sort=False):
        k = known[known["customer_id"] == cid]
        if k.empty:
            continue
        times = k["resolved_at"].to_numpy()
        csum = np.cumsum(k["b"].to_numpy())
        idx = np.searchsorted(times, g["created_at"].to_numpy(), side="left")  # resolved strictly before
        n = idx.astype(float)
        s = np.where(idx > 0, csum[np.maximum(idx - 1, 0)], 0.0)
        out_n[g.index] = n
        out_rate[g.index] = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    d["cust_prior_resolved"] = out_n
    d["cust_prior_breach_rate"] = pd.Series(out_rate).fillna(d["sla_breached"].astype(float).mean())
    return d


def metrics(y, p, thr):
    yhat = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    return {"threshold": round(float(thr), 3), "precision": round(precision_score(y, yhat, zero_division=0), 3),
            "recall": round(recall_score(y, yhat), 3), "f1": round(f1_score(y, yhat), 3),
            "roc_auc": round(roc_auc_score(y, p), 3) if len(set(p)) > 1 else 0.5,
            "pr_auc": round(average_precision_score(y, p), 3),
            "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}}


def best_threshold(y, p):
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / np.maximum(prec + rec, 1e-9)
    i = int(np.nanargmax(f1[:-1]))
    return float(thr[i])


def main():
    f = load_fact()
    dims = load_dims()
    d = build_features(f, dims)
    d = d[d["in_sla_population"]].copy()            # outcome must be known
    d["y"] = d["sla_breached"].astype(int)
    m = d["created_at"]
    train = d[m < "2025-04-01"]
    valid = d[(m >= "2025-04-01") & (m < "2025-07-01")]
    test = d[m >= "2025-07-01"]

    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20, sparse_output=False), CAT),
                             ("num", StandardScaler(), NUM)])
    models = {
        "Logistic regression": Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000, C=1.0,
                                                                                   class_weight="balanced"))]),
        "Random forest": Pipeline([("pre", pre), ("clf", RandomForestClassifier(
            n_estimators=300, min_samples_leaf=20, class_weight="balanced_subsample", n_jobs=-1,
            random_state=SEED))]),
        "Gradient boosting": Pipeline([("pre", pre), ("clf", HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0,
            class_weight="balanced", random_state=SEED))]),
    }
    results, probs = {}, {}
    # Baselines: always "no breach"; and a business rule (P1/P2 on a Platinum or Gold contract)
    y_te = test["y"].to_numpy()
    dummy = DummyClassifier(strategy="prior").fit(train[CAT + NUM], train["y"])
    results["Baseline: always 'no breach'"] = {"valid": None,
                                               "test": metrics(y_te, dummy.predict_proba(test[CAT + NUM])[:, 1], 0.5)}
    rule = lambda x: (x["priority"].isin(["P1", "P2"]) & x["sla_level"].isin(["Platinum", "Gold"])).astype(float)  # noqa: E731
    results["Baseline: rule (P1/P2 on Platinum/Gold)"] = {"valid": metrics(valid["y"], rule(valid), 0.5),
                                                          "test": metrics(y_te, rule(test).to_numpy(), 0.5)}
    for name, pipe in models.items():
        pipe.fit(train[CAT + NUM], train["y"])
        pv = pipe.predict_proba(valid[CAT + NUM])[:, 1]
        thr = best_threshold(valid["y"], pv)
        pt = pipe.predict_proba(test[CAT + NUM])[:, 1]
        probs[name] = pt
        results[name] = {"valid": metrics(valid["y"], pv, thr), "test": metrics(y_te, pt, thr)}
        print(f"{name:22s} valid AUC {results[name]['valid']['roc_auc']:.3f}  test AUC "
              f"{results[name]['test']['roc_auc']:.3f}  F1 {results[name]['test']['f1']:.3f}")

    # Chosen on VALIDATION ROC-AUC. Models within 0.005 of the best are treated as tied and the
    # simplest (most explainable) is preferred: logistic regression > random forest > boosting.
    best = max(results[n]["valid"]["roc_auc"] for n in models)
    chosen = next(n for n in models if results[n]["valid"]["roc_auc"] >= best - 0.005)
    imp = permutation_importance(models[chosen], test[CAT + NUM], y_te, scoring="roc_auc", n_repeats=5,
                                 random_state=SEED, n_jobs=-1)
    importance = (pd.DataFrame({"feature": CAT + NUM, "auc_drop": imp.importances_mean,
                                "std": imp.importances_std}).sort_values("auc_drop", ascending=False))

    # Lift: breach rate in the top 10% / 20% risk scores
    pt = probs[chosen]
    order = np.argsort(-pt)
    lift = {}
    for share in (0.1, 0.2):
        k = int(len(pt) * share)
        lift[f"top_{int(share * 100)}pct_breach_rate"] = round(float(100 * y_te[order[:k]].mean()), 1)
        lift[f"top_{int(share * 100)}pct_share_of_breaches"] = round(float(100 * y_te[order[:k]].sum() / y_te.sum()), 1)
    out = {"split": {"train": [str(train["created_at"].min().date()), str(train["created_at"].max().date()), len(train)],
                     "valid": [str(valid["created_at"].min().date()), str(valid["created_at"].max().date()), len(valid)],
                     "test": [str(test["created_at"].min().date()), str(test["created_at"].max().date()), len(test)]},
           "breach_rate": {"train": round(100 * train["y"].mean(), 2), "valid": round(100 * valid["y"].mean(), 2),
                           "test": round(100 * test["y"].mean(), 2)},
           "features": {"categorical": CAT, "numeric": NUM}, "results": results, "chosen_model": chosen,
           "permutation_importance": importance.round(4).to_dict("records"), "lift": lift}
    (OUT / "model_metrics.json").write_text(json.dumps(out, indent=2) + "\n")

    # figures
    style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for (name, p), col in zip(probs.items(), SERIES):
        fpr, tpr, _ = roc_curve(y_te, p)
        axes[0].plot(fpr, tpr, color=col, label=f"{name} (AUC {roc_auc_score(y_te, p):.2f})")
        pr, rc, _ = precision_recall_curve(y_te, p)
        axes[1].plot(rc, pr, color=col, label=f"{name} (AP {average_precision_score(y_te, p):.2f})")
    axes[0].plot([0, 1], [0, 1], color=INK_2, linestyle="--", linewidth=1, label="Random")
    axes[1].axhline(y_te.mean(), color=INK_2, linestyle="--", linewidth=1, label="Prevalence")
    axes[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC - test set (H2 2025)")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision-recall - test set")
    axes[0].legend(loc="lower right", fontsize=8)
    axes[1].legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    img_roc = save(fig, "13_model_roc_pr")
    fig, ax = plt.subplots(figsize=(7, 4))
    top = importance.head(10)[::-1]
    ax.barh(top["feature"], top["auc_drop"], xerr=top["std"], color=SERIES[0], height=.55,
            error_kw={"ecolor": INK_2, "capsize": 3})
    ax.set_xlabel("Drop in test ROC-AUC when the feature is shuffled")
    ax.set_title(f"Permutation importance - {chosen}")
    ax.grid(axis="y", visible=False)
    img_imp = save(fig, "14_model_importance")

    rows = []
    for name, r in results.items():
        t = r["test"]
        rows.append({"model": name, "threshold": t["threshold"], "precision": t["precision"], "recall": t["recall"],
                     "f1": t["f1"], "roc_auc": t["roc_auc"], "pr_auc": t["pr_auc"],
                     "valid_roc_auc": r["valid"]["roc_auc"] if r["valid"] else None})
    cm = results[chosen]["test"]["confusion"]
    report = [
        "# SLA breach-risk model", "",
        "> Synthetic data. Generated by `analytics/model.py`; all metrics in `analytics/outputs/model_metrics.json`.", "",
        "## Question", "", "At the moment a ticket is **logged**, how likely is it to breach its SLA? A risk score at "
        "creation lets a Team Lead route or prioritise tickets before the clock runs out.", "",
        "## Leakage control", "",
        "Only information available at creation time is used. History features (team load in the previous 7 days, "
        "customer's prior tickets and prior breach rate) are computed from **earlier** tickets only, and a prior "
        "breach counts only if that ticket was already resolved when the new ticket arrived.", "",
        "Excluded because they are only known later: resolution time, first response, escalation, reopens, FCR, "
        "root cause, resolution type, knowledge-base use, CSAT, status.", "",
        f"Categorical features: {', '.join(CAT)}. Numeric features: {', '.join(NUM)}.", "",
        "## Chronological split", "",
        md_table(pd.DataFrame([{"set": k, "from": v[0], "to": v[1], "tickets": v[2],
                                "breach_rate_pct": out["breach_rate"][k]} for k, v in out["split"].items()])), "",
        "The decision threshold for each model is chosen on the **validation** quarter (maximum F1), and the "
        "final model is chosen on validation ROC-AUC. The test half-year is scored once. The breach rate "
        "rises over time, so the test set is harder than the training data - a realistic deployment condition.", "",
        "## Results on the test set (H2 2025)", "", md_table(pd.DataFrame(rows)), "",
        f"Chosen model: **{chosen}** (highest validation ROC-AUC; models within 0.005 of the best are treated "
        "as tied and the simplest, most explainable one is preferred). Confusion matrix on test at threshold "
        f"{results[chosen]['test']['threshold']}:", "",
        "| | Predicted no breach | Predicted breach |", "|---|---:|---:|",
        f"| **Actual no breach** | {cm['tn']:,} | {cm['fp']:,} |",
        f"| **Actual breach** | {cm['fn']:,} | {cm['tp']:,} |", "",
        f"**Lift.** The 10% of test tickets with the highest risk score breach at {lift['top_10pct_breach_rate']}% "
        f"(vs {out['breach_rate']['test']}% overall) and contain {lift['top_10pct_share_of_breaches']}% of all "
        f"breaches; the top 20% contain {lift['top_20pct_share_of_breaches']}%.", "",
        f"![ROC and PR curves]({img_roc})", "", f"![Permutation importance]({img_imp})", "",
        "## Limitations", "",
        "1. **Synthetic data.** The generator's breach mechanism is known (docs/06_synthetic_data_design.md); "
        "a model that recovers it is evidence the pipeline works, not that these features predict breaches "
        "in a real service desk.",
        "2. **Moderate discrimination by design.** Most of the variation in resolution time comes from "
        "events after logging (escalation, reopens, the work itself) that the model is deliberately not allowed "
        "to see. A model scored again at first response, or hourly while a ticket is open, would do better.",
        "3. **Calibration** was not tuned (class weights shift probabilities up); scores rank tickets well "
        "but should not be read as exact probabilities without calibration (e.g. isotonic on validation).",
        "4. **Drift.** Breach rates rise over the period; the model must be retrained regularly and monitored "
        "on recent data.",
        "5. **Associations, not causes.** Feature importance shows what helps prediction, not what to change; "
        "for example SLA level matters because targets differ, not because customers behave differently.",
        "6. **Fairness to teams.** Team is a feature; a risk score must not be used to judge individual agents.",
    ]
    (ROOT / "docs" / "model_report.md").write_text("\n".join(report) + "\n")
    print(f"Chosen: {chosen}; test: {results[chosen]['test']}")
    print(f"Lift: {lift}")


if __name__ == "__main__":
    main()
