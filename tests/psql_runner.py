"""
Test-only query executor: runs the backend's parameterised SQL through `psql`.

Lets the endpoint logic in backend/app/services.py be verified against the
real database on machines where psycopg / FastAPI are not installed. Values
are rendered as quoted SQL literals (strings escaped, lists as text[] arrays).
This is for tests only - the production API uses psycopg server-side
parameter binding (backend/app/db.py), never string formatting.
"""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from reconcile_db import load_env  # noqa: E402


def _literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, datetime):
        return f"'{v.isoformat(sep=' ')}'::timestamp"
    if isinstance(v, date):
        return f"'{v.isoformat()}'::date"
    if isinstance(v, (list, tuple)):
        return "ARRAY[" + ",".join(_literal(x) for x in v) + "]::text[]"
    s = str(v).replace("'", "''")
    return f"E'{s.replace(chr(92), chr(92) * 2)}'" if "\\" in s else f"'{s}'"


def render(sql: str, params: dict) -> str:
    def sub(m):
        return _literal(params[m.group(1)])
    return re.sub(r"%\((\w+)\)s", sub, sql)


def _convert(df: pd.DataFrame) -> list[dict]:
    rows = []
    for rec in df.to_dict("records"):
        out = {}
        for k, v in rec.items():
            if isinstance(v, float) and pd.isna(v):
                v = None
            elif v == "t":
                v = True
            elif v == "f":
                v = False
            elif isinstance(v, float) and v.is_integer() and k.endswith(("tickets", "count", "incidents",
                                                                         "responses", "population", "breaches")):
                v = int(v)
            out[k] = v
        rows.append(out)
    return rows


def run(queries: dict) -> dict:
    env, db = load_env()
    out = {}
    for name, (sql, params) in queries.items():
        r = subprocess.run(["psql", "-X", "-q", "--csv", "-v", "ON_ERROR_STOP=1", "-d", db],
                           input=render(sql, params), capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"{name}: {r.stderr.strip()}")
        df = pd.read_csv(io.StringIO(r.stdout), keep_default_na=False, na_values=[""]) if r.stdout.strip() else pd.DataFrame()
        out[name] = _convert(df)
    return out


def available() -> bool:
    if not shutil.which("psql"):
        return False
    try:
        run({"x": ("SELECT 1 AS one", {})})
        return True
    except Exception:  # noqa: BLE001
        return False
