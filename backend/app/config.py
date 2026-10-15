"""Settings read from environment variables (and the project .env file if present).

No credentials live in code: DB_APP_PASSWORD must come from the environment / .env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines). Real environment variables win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "it_service_intelligence"))
    db_user: str = field(default_factory=lambda: os.getenv("DB_APP_USER", "itsi_app"))
    db_password: str = field(default_factory=lambda: os.getenv("DB_APP_PASSWORD", ""))
    pool_min: int = field(default_factory=lambda: int(os.getenv("DB_POOL_MIN", "1")))
    pool_max: int = field(default_factory=lambda: int(os.getenv("DB_POOL_MAX", "10")))
    statement_timeout_ms: int = field(default_factory=lambda: int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "5000")))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in os.getenv("API_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    def conninfo(self) -> str:
        # password is passed separately via kwargs, never formatted into logs
        return (f"host={self.db_host} port={self.db_port} dbname={self.db_name} user={self.db_user} "
                f"application_name=itsi-api")


settings = Settings()
