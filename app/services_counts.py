"""Exact row counts for the public stats.

The home page promises a verifiable record, so the numbers must be real counts. The database's
own row estimates (pg_stat n_live_tup) can lag or read 0 on a table that has not been analyzed
recently, so they are not used. A short in-process cache keeps page views cheap.
"""
import time

from sqlalchemy import inspect, text

TABLES = (
    "pinnacle_sentinel_filings",
    "pinnacle_sentinel_financial_facts",
    "pinnacle_sentinel_flag_events",
    "pinnacle_sentinel_quant_scores",
)

_cache = {"at": None, "counts": None}


def exact_counts(db, ttl=300, tables=TABLES):
    """{table: exact COUNT(*)}; a table that does not exist counts as 0."""
    now = time.monotonic()
    if ttl and _cache["counts"] is not None and _cache["at"] is not None and now - _cache["at"] < ttl:
        return dict(_cache["counts"])
    inspector = inspect(db.get_bind())
    counts = {}
    for name in tables:
        if inspector.has_table(name):
            counts[name] = int(db.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar() or 0)
        else:
            counts[name] = 0
    if ttl:
        _cache["at"], _cache["counts"] = now, dict(counts)
    return counts
