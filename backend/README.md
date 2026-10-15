# Backend - FastAPI

Read-only REST API over the PostgreSQL `analytics` schema. **Synthetic data.**

```bash
bash scripts/start_api.sh          # Windows: scripts\start_api.ps1   ->  http://localhost:8000/docs
```

| Module | Responsibility |
|---|---|
| `app/config.py` | Settings from environment / `.env` (no credentials in code) |
| `app/db.py` | psycopg 3 connection pool; read-only sessions with a statement timeout; Decimal/date to JSON |
| `app/filters.py` | Filter and paging validation (raises `FilterError` → 422); parameterised WHERE builder; sort whitelists |
| `app/services.py` | One function per endpoint: SQL plus response shaping. Has no framework imports, so it can be tested directly |
| `app/main.py` | Routes, dependencies, CORS, request logging (`x-request-id`), error handlers (422/503) |

Endpoints and real example responses: [`docs/api_reference.md`](../docs/api_reference.md).
Tests: `tests/test_backend.py` (SQL against the real database) and `tests/test_api.py` (HTTP).
