"""Shared loading, plotting style and small statistical helpers for analytics/."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "analytics" / "outputs"
FIG = OUT / "figures"

# Validated categorical palette (dataviz reference palette, fixed order, light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
PRIORITY_COLOR = dict(zip(["P1", "P2", "P3", "P4"], SERIES[:4]))

BOOL_COLS = ["escalation_flag", "is_reopened", "first_contact_resolution", "knowledge_base_used",
             "is_incident", "is_open", "is_resolved", "is_cancelled", "is_out_of_hours",
             "customer_is_placeholder", "in_sla_population", "in_duration_population",
             "in_response_population", "in_fcr_population", "has_valid_csat", "sla_breached",
             "response_sla_met", "fcr_achieved", "is_repeat_incident", "is_open_past_target",
             "is_resolution_outlier", "is_invalid_timestamp", "is_orphan_customer",
             "is_agent_team_mismatch"]


def _bool(s: pd.Series) -> pd.Series:
    return s.map({"t": True, "f": False, "true": True, "false": False, True: True, False: False})


def load_fact() -> pd.DataFrame:
    """analytics.fact_tickets as exported by database/export_analytics.sql."""
    f = pd.read_csv(PROCESSED / "fact_tickets.csv",
                    parse_dates=["created_at", "first_response_at", "resolved_at"],
                    low_memory=False)
    for c in BOOL_COLS:
        if c in f:
            f[c] = _bool(f[c])
    f["created_month"] = pd.to_datetime(f["created_month"])
    return f


def load_dims() -> dict[str, pd.DataFrame]:
    return {n: pd.read_csv(PROCESSED / f"dim_{n}.csv")
            for n in ["customer", "agent", "team", "category", "sla_target"]}


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "xtick.color": INK_2, "ytick.color": INK_2, "text.color": INK,
        "font.size": 10, "legend.frameon": False, "lines.linewidth": 2,
        "figure.dpi": 110, "savefig.dpi": 140, "savefig.bbox": "tight",
    })


def save(fig, name: str) -> str:
    FIG.mkdir(parents=True, exist_ok=True)
    path = FIG / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return f"../analytics/outputs/figures/{name}.png"


def wilson_ci(successes: float, n: float, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion (robust for small n)."""
    if n == 0:
        return (np.nan, np.nan)
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (centre - half, centre + half)


def cramers_v(table: pd.DataFrame) -> float:
    from scipy.stats import chi2_contingency
    chi2 = chi2_contingency(table, correction=False)[0]
    n = table.to_numpy().sum()
    r, k = table.shape
    return float(np.sqrt(chi2 / (n * (min(r, k) - 1))))


def md_table(df: pd.DataFrame, floatfmt: str = "{:,.2f}") -> str:
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else floatfmt.format(v)
        if isinstance(v, (int, np.integer)):
            return f"{v:,}"
        return str(v)
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)
