"""investigation_search: retry refused searches; a failed or truncated search must fail the run loudly."""
import os, sys
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from app.services import investigation_search as inv


class _Q:
    def filter(self, *a, **k): return self
    def all(self): return []


class _FakeDB:
    def __init__(self): self.added = []; self.committed = False
    def query(self, *a, **k): return _Q()
    def add(self, x): self.added.append(x)
    def commit(self): self.committed = True
    def close(self): pass


def _hit(i):
    return {"_source": {"ciks": ["1"], "file_date": f"2026-08-0{i}", "root_forms": ["8-K"],
                        "adsh": f"a{i}", "display_names": []}}


def _data(n, total=None):
    return {"hits": {"total": {"value": n if total is None else total}, "hits": [_hit(i) for i in range(1, n + 1)]}}


@pytest.fixture
def db(monkeypatch):
    fake = _FakeDB()
    monkeypatch.setattr(inv, "SessionLocal", lambda: fake)
    monkeypatch.setattr(inv, "load_universe_ciks_and_tickers", lambda: {"0000000001": "T"})
    monkeypatch.setattr(inv, "REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(inv, "RETRY_BACKOFF_SECONDS", [0, 0])
    monkeypatch.setattr(inv, "INVESTIGATION_QUERIES", [("alpha", "sec_subpoena"), ("beta", "sec_investigation")])
    return fake


def test_clean_run_does_not_raise(db, monkeypatch):
    monkeypatch.setattr(inv, "search_efts", lambda *a, **k: _data(1))
    inv.ingest("2026-08-01", "2026-08-08")
    assert db.committed and len(db.added) == 2


def test_transient_refusal_is_retried(db, monkeypatch):
    calls = {"n": 0}
    def flaky(q, *a, **k):
        if q == "alpha":
            calls["n"] += 1
            if calls["n"] < 3:
                return None
        return _data(1)
    monkeypatch.setattr(inv, "search_efts", flaky)
    inv.ingest("2026-08-01", "2026-08-08")          # must not raise
    assert calls["n"] == 3 and len(db.added) == 2


def test_persistent_failure_raises_but_keeps_other_results(db, monkeypatch):
    monkeypatch.setattr(inv, "search_efts", lambda q, *a, **k: None if q == "alpha" else _data(1))
    with pytest.raises(RuntimeError, match="NOT complete.*alpha"):
        inv.ingest("2026-08-01", "2026-08-08")
    assert db.committed and len(db.added) == 1      # beta's result was saved


def test_truncated_results_raise(db, monkeypatch):
    monkeypatch.setattr(inv, "search_efts", lambda q, *a, **k: _data(1, total=250))
    with pytest.raises(RuntimeError, match="only 1 of 250"):
        inv.ingest("2026-08-01", "2026-08-08")
