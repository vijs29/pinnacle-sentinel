"""edgar_ingest must fail loudly when many lookups fail; the scheduler must run the daily jobs."""
import os, sys
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from app.services import edgar_ingest


class _FakeDB:
    def query(self, *a, **k):
        class Q:
            def all(self_inner): return []
        return Q()
    def add(self, x): pass
    def commit(self): pass
    def close(self): pass


def _setup(monkeypatch, n, failing):
    universe = [{"cik": str(i), "ticker": f"T{i}", "company_name": f"C{i}"} for i in range(n)]
    monkeypatch.setattr(edgar_ingest, "load_universe", lambda: universe)
    monkeypatch.setattr(edgar_ingest, "SessionLocal", lambda: _FakeDB())
    monkeypatch.setattr(edgar_ingest, "REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(edgar_ingest, "fetch_submissions", lambda cik: None if int(cik) < failing else {"filings": {"recent": {}}})


def test_ingest_raises_when_many_lookups_fail(monkeypatch):
    _setup(monkeypatch, 10, failing=5)
    with pytest.raises(RuntimeError, match="NOT up to date"):
        edgar_ingest.ingest()


def test_ingest_tolerates_a_few_failures(monkeypatch):
    _setup(monkeypatch, 10, failing=1)
    edgar_ingest.ingest()      # 10% failed: ok


def test_scheduler_registers_daily_jobs(monkeypatch):
    pytest.importorskip("apscheduler")
    from app.services import scheduler_service as ss
    monkeypatch.setenv("ENABLE_SCHEDULER", "1")
    ss._scheduler = None
    ss.start_scheduler()
    ids = {j["id"] for j in ss.scheduler_status()["jobs"]}
    ss._scheduler.shutdown(wait=False); ss._scheduler = None
    assert {"edgar_ingest", "form4_ingest", "flag_detector_8k", "going_concern", "insider_cluster",
            "investigation_search", "xbrl_ingest", "quant_scores", "quant_flags"} <= ids
