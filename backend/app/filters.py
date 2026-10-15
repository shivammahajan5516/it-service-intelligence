"""Dashboard filters: validation and a parameterised WHERE-clause builder.

Pure Python (no FastAPI / database imports) so it can be unit tested anywhere.
User input never reaches SQL text: values go into the params dict, column
names and sort expressions come only from fixed whitelists in this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

PRIORITIES = ("P1", "P2", "P3", "P4")
TEAM_RE = re.compile(r"^T\d{2}$")
MAX_LABEL = 64
MAX_LIST = 20
MAX_RANGE_DAYS = 3660


class FilterError(ValueError):
    """Raised for invalid filter input; the API turns it into HTTP 422."""


@dataclass(frozen=True)
class Filters:
    start: date | None = None
    end: date | None = None
    priorities: tuple[str, ...] = ()
    teams: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()

    def previous_period(self) -> "Filters | None":
        """Same-length window immediately before [start, end] (FR-02)."""
        if not (self.start and self.end):
            return None
        days = (self.end - self.start).days + 1
        prev_end = self.start - timedelta(days=1)
        return Filters(prev_end - timedelta(days=days - 1), prev_end, self.priorities, self.teams,
                       self.categories, self.regions)

    def as_dict(self) -> dict:
        return {"start_date": self.start.isoformat() if self.start else None,
                "end_date": self.end.isoformat() if self.end else None,
                "priority": list(self.priorities), "team": list(self.teams),
                "category": list(self.categories), "region": list(self.regions)}


def _split(values: list[str] | str | None) -> tuple[str, ...]:
    """Accept repeated params (?team=T01&team=T02) and comma lists (?team=T01,T02)."""
    if values is None:
        return ()
    if isinstance(values, str):
        values = [values]
    out: list[str] = []
    for v in values:
        out.extend(p.strip() for p in v.split(",") if p.strip())
    if len(out) > MAX_LIST:
        raise FilterError(f"At most {MAX_LIST} values per filter")
    return tuple(dict.fromkeys(out))  # de-duplicate, keep order


def _parse_date(value: str | date | None, name: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise FilterError(f"{name} must be a date in YYYY-MM-DD format") from exc


def build_filters(start_date=None, end_date=None, priority=None, team=None, category=None, region=None,
                  allowed_categories: set[str] | None = None,
                  allowed_regions: set[str] | None = None) -> Filters:
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if start and end and start > end:
        raise FilterError("start_date must be on or before end_date")
    if start and end and (end - start).days > MAX_RANGE_DAYS:
        raise FilterError("Date range is too long")
    pr = tuple(p.upper() for p in _split(priority))
    bad = [p for p in pr if p not in PRIORITIES]
    if bad:
        raise FilterError(f"Unknown priority: {', '.join(bad)} (use P1-P4)")
    tm = tuple(t.upper() for t in _split(team))
    bad = [t for t in tm if not TEAM_RE.match(t)]
    if bad:
        raise FilterError(f"Invalid team id: {', '.join(bad)} (expected e.g. T01)")
    cats, regs = _split(category), _split(region)
    for label, values, allowed in (("category", cats, allowed_categories), ("region", regs, allowed_regions)):
        too_long = [v for v in values if len(v) > MAX_LABEL]
        if too_long:
            raise FilterError(f"{label} value too long")
        if allowed is not None:
            unknown = [v for v in values if v not in allowed]
            if unknown:
                raise FilterError(f"Unknown {label}: {', '.join(unknown)}")
    return Filters(start, end, pr, tm, cats, regs)


def where_clause(f: Filters, alias: str = "f", prefix: str = "") -> tuple[str, dict]:
    """Return ("cond AND cond", params). Placeholders use psycopg's %(name)s style."""
    conds: list[str] = []
    params: dict = {}

    def add(cond: str, key: str, value):
        conds.append(cond.format(a=alias, k=prefix + key))
        params[prefix + key] = value

    if f.start:
        add("{a}.created_at >= %({k})s", "start", f.start)
    if f.end:
        add("{a}.created_at < %({k})s", "end_excl", f.end + timedelta(days=1))
    if f.priorities:
        add("{a}.priority = ANY(%({k})s)", "priorities", list(f.priorities))
    if f.teams:
        add("{a}.team_id = ANY(%({k})s)", "teams", list(f.teams))
    if f.categories:
        add("{a}.category = ANY(%({k})s)", "categories", list(f.categories))
    if f.regions:
        add("{a}.region = ANY(%({k})s)", "regions", list(f.regions))
    return (" AND ".join(conds) if conds else "TRUE"), params


def like_pattern(text: str) -> str:
    """Escape LIKE wildcards in user search text."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@dataclass(frozen=True)
class Page:
    page: int = 1
    page_size: int = 25
    sort: str = ""
    order: str = "desc"
    search: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def build_page(page=1, page_size=25, sort="", order="desc", search="", allowed_sorts=(), default_sort=""):
    try:
        page, page_size = int(page), int(page_size)
    except (TypeError, ValueError) as exc:
        raise FilterError("page and page_size must be integers") from exc
    if page < 1:
        raise FilterError("page must be >= 1")
    if not 1 <= page_size <= 100:
        raise FilterError("page_size must be between 1 and 100")
    sort = sort or default_sort
    if sort not in allowed_sorts:
        raise FilterError(f"sort must be one of: {', '.join(allowed_sorts)}")
    order = (order or "desc").lower()
    if order not in ("asc", "desc"):
        raise FilterError("order must be asc or desc")
    search = (search or "").strip()
    if len(search) > 100:
        raise FilterError("search is too long")
    return Page(page, page_size, sort, order, search)
