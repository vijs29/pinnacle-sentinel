from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.services_counts import exact_counts


def _db(rows):
    eng = create_engine("sqlite://")
    S = sessionmaker(bind=eng)
    db = S()
    for table, n in rows.items():
        db.execute(text(f'CREATE TABLE "{table}" (id INTEGER)'))
        for i in range(n):
            db.execute(text(f'INSERT INTO "{table}" VALUES ({i})'))
    db.commit()
    return db


def test_counts_are_exact():
    db = _db({"a": 7, "b": 0, "c": 1234})
    assert exact_counts(db, ttl=0, tables=("a", "b", "c")) == {"a": 7, "b": 0, "c": 1234}


def test_missing_table_counts_as_zero():
    db = _db({"a": 3})
    assert exact_counts(db, ttl=0, tables=("a", "nope")) == {"a": 3, "nope": 0}


def test_cache_serves_within_ttl_and_refreshes_without():
    db = _db({"a": 2})
    assert exact_counts(db, ttl=300, tables=("a",)) == {"a": 2}
    db.execute(text('INSERT INTO "a" VALUES (99)')); db.commit()
    assert exact_counts(db, ttl=300, tables=("a",)) == {"a": 2}   # cached
    assert exact_counts(db, ttl=0, tables=("a",)) == {"a": 3}     # fresh


def test_stats_use_exact_counts_not_estimates():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1].joinpath("app/api/main.py").read_text()
    body = src[src.index("def get_stats"):src.index("# Static UI serving")]
    assert "exact_counts(db)" in body
    assert "n_live_tup" not in body


def test_stats_cover_the_four_sentinel_tables():
    from app.services_counts import TABLES
    assert set(TABLES) == {
        "pinnacle_sentinel_filings", "pinnacle_sentinel_financial_facts",
        "pinnacle_sentinel_flag_events", "pinnacle_sentinel_quant_scores",
    }

def test_cache_expires_after_ttl(monkeypatch):
    import app.services_counts as sc
    sc._cache.update(at=None, counts=None)
    clock = [1000.0]
    monkeypatch.setattr(sc.time, "monotonic", lambda: clock[0])
    db = _db({"a": 2})
    assert exact_counts(db, ttl=300, tables=("a",)) == {"a": 2}
    db.execute(text('INSERT INTO "a" VALUES (99)')); db.commit()
    clock[0] += 299
    assert exact_counts(db, ttl=300, tables=("a",)) == {"a": 2}   # still inside the window
    clock[0] += 2
    assert exact_counts(db, ttl=300, tables=("a",)) == {"a": 3}   # window passed: counted again
    sc._cache.update(at=None, counts=None)
