"""PostgreSQL connection management (psycopg 3 connection pool).

* One pool per process, opened on startup and closed on shutdown (see main.lifespan).
* Every session is READ ONLY with a statement timeout - defence in depth on top of
  the read-only database role created by database/grants.sql.
* All queries are parameterised: SQL text and values travel separately.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

log = logging.getLogger("itsi.db")
_pool: ConnectionPool | None = None


def _configure(conn) -> None:
    conn.read_only = True
    with conn.cursor() as cur:
        cur.execute(f"SET statement_timeout = {int(settings.statement_timeout_ms)}")
    conn.commit()


def open_pool() -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.conninfo(),
            kwargs={"password": settings.db_password, "row_factory": dict_row, "autocommit": False},
            min_size=settings.pool_min, max_size=settings.pool_max, configure=_configure,
            open=False, name="itsi")
        _pool.open(wait=False)
        log.info("Database pool opened (%s@%s:%s/%s)", settings.db_user, settings.db_host,
                 settings.db_port, settings.db_name)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        log.info("Database pool closed")


def _jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def run(queries: dict[str, tuple[str, dict]]) -> dict[str, list[dict]]:
    """Execute named parameterised queries in one read-only transaction."""
    if _pool is None:
        open_pool()
    assert _pool is not None
    out: dict[str, list[dict]] = {}
    with _pool.connection(timeout=10) as conn:
        with conn.cursor() as cur:
            for name, (sql, params) in queries.items():
                cur.execute(sql, params)
                out[name] = [{k: _jsonable(v) for k, v in row.items()} for row in cur.fetchall()]
    return out
