#!/usr/bin/env python3
"""
Execute every numbered query in database/queries/*.sql against PostgreSQL
and build docs/sql_analysis.md from the ACTUAL results.

  * Queries run as the read-only application role (DB_APP_USER in .env),
    which proves the analysis needs nothing beyond the analytics layer.
  * Each result is saved to database/query_results/Qnn.csv.
  * Business interpretations live in database/queries/interpretations.md
    ("## Qnn" sections). They were written after reading the results; if the
    data is regenerated with another seed, re-read and update them.

Query block format inside the .sql files:
    -- @Q01
    -- title: ...
    -- question: ...
    -- technique: ...
    -- why: ...
    SELECT ...;

Usage:  python scripts/run_sql_analysis.py [--strict]
        --strict  fail if any query has no interpretation
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reconcile_db import load_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QDIR = ROOT / "database" / "queries"
OUT = ROOT / "database" / "query_results"
DOC = ROOT / "docs" / "sql_analysis.md"
MAX_ROWS_IN_DOC = 25


def parse_queries():
    queries = []
    for path in sorted(QDIR.glob("*.sql")):
        text = path.read_text()
        blocks = re.split(r"^-- @(Q\d+)\s*$", text, flags=re.M)
        for qid, body in zip(blocks[1::2], blocks[2::2]):
            meta, sql_lines = {}, []
            for line in body.strip().splitlines():
                m = re.match(r"^-- (title|question|technique|why):\s*(.*)$", line)
                if m and not sql_lines:
                    meta[m.group(1)] = m.group(2).strip()
                elif line.startswith("-- ====") and not sql_lines:
                    continue
                else:
                    sql_lines.append(line)
            sql = "\n".join(sql_lines).strip()
            queries.append({"id": qid, "file": path.name, "sql": sql, **meta})
    return queries


def parse_interpretations():
    p = QDIR / "interpretations.md"
    if not p.exists():
        return {}
    parts = re.split(r"^## (Q\d+)\s*$", p.read_text(), flags=re.M)
    return {qid: body.strip() for qid, body in zip(parts[1::2], parts[2::2])}


def run(sql: str):
    env, db = load_env()
    t0 = time.perf_counter()
    out = subprocess.run(["psql", "-X", "-q", "--csv", "-v", "ON_ERROR_STOP=1", "-d", db],
                         input=sql, capture_output=True, text=True, env=env)
    ms = (time.perf_counter() - t0) * 1000
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    df = pd.read_csv(io.StringIO(out.stdout), keep_default_na=False) if out.stdout.strip() else pd.DataFrame()
    return df, ms


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_(no rows)_"
    shown = df.head(MAX_ROWS_IN_DOC)
    head = "| " + " | ".join(map(str, shown.columns)) + " |"
    sep = "|" + "|".join("---" for _ in shown.columns) + "|"
    rows = ["| " + " | ".join(str(v).replace("|", "\\|") for v in r) + " |" for r in shown.itertuples(index=False)]
    note = f"\n\n_Showing {MAX_ROWS_IN_DOC} of {len(df)} rows - full result in the CSV._" if len(df) > MAX_ROWS_IN_DOC else ""
    return "\n".join([head, sep, *rows]) + note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    queries, interp = parse_queries(), parse_interpretations()
    env, db = load_env()
    failures, missing = [], []

    toc = ["| # | Title | File | Technique |", "|---|---|---|---|"]
    sections = []
    for q in queries:
        try:
            df, ms = run(q["sql"])
        except RuntimeError as e:
            failures.append((q["id"], str(e)))
            print(f"FAIL {q['id']}: {e}")
            continue
        df.to_csv(OUT / f"{q['id']}.csv", index=False)
        print(f"OK   {q['id']}  {len(df):>4} rows  {ms:7.1f} ms  {q.get('title', '')}")
        text = interp.get(q["id"])
        if not text:
            missing.append(q["id"])
            text = "_Interpretation not yet written._"
        toc.append(f"| [{q['id']}](#{q['id'].lower()}) | {q.get('title', '')} | `{q['file']}` | {q.get('technique', '')} |")
        sections.append("\n".join([
            f"## {q['id']}", "", f"### {q.get('title', '')}", "",
            f"**1. Business question.** {q.get('question', '')}", "",
            "**2. SQL solution** (`database/queries/" + q["file"] + "`)", "", "```sql", q["sql"], "```", "",
            f"**3. Why this technique.** {q.get('technique', '')}. {q.get('why', '')}", "",
            f"**4. Actual result** - {len(df)} row(s), {ms:.0f} ms including client round-trip; "
            f"saved to `database/query_results/{q['id']}.csv`", "", md_table(df), "",
            f"**5. Business interpretation.** {text}", "", "---", ""]))

    header = [
        "# SQL analysis - 37 queries executed against the PostgreSQL database", "",
        "> Synthetic data (Northbridge Managed Services Ltd is fictional). Every result below was produced "
        "by running the query against the database built by `database/build_database.*`; nothing is typed in "
        "by hand. Regenerate with `python scripts/run_sql_analysis.py`.", "",
        f"- Database: `{db}`, queried as the read-only role `{env.get('PGUSER', '(default)')}`",
        "- Source: `analytics` schema only (`fact_tickets` and the KPI / dimension views)",
        "- KPI definitions: `docs/04_kpi_catalogue.md`; population rules: `docs/05_business_rules.md`",
        "- Correlation is not causation: where a query shows an association, the interpretation says so. "
        "The causal mechanisms in this synthetic data are listed in `docs/06_synthetic_data_design.md`.",
        "", "## Contents", "", *toc, "", "---", ""]
    DOC.write_text("\n".join(header + sections))

    print(f"\n{len(queries) - len(failures)}/{len(queries)} queries succeeded -> {DOC.relative_to(ROOT)}")
    if missing:
        print(f"Missing interpretations: {', '.join(missing)}")
    if failures or (args.strict and missing):
        sys.exit(1)


if __name__ == "__main__":
    main()
