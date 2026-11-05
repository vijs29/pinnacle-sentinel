"""A failed or missed scheduled job must send a push; a good job must not; a broken alert must not break the job."""
import os, sys
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from app.services import alerts, scheduler_service as ss


@pytest.fixture
def pushes(monkeypatch):
    sent = []
    monkeypatch.setattr(alerts, "send_push", lambda title, message, priority=1: sent.append((title, message, priority)) or True)
    return sent


def test_failed_job_sends_a_push_naming_the_job_and_error(pushes):
    def boom(): raise RuntimeError("EDGAR said no")
    ss._run_safely("edgar_ingest", boom)           # must not raise
    assert len(pushes) == 1
    assert "edgar_ingest" in pushes[0][0] and "EDGAR said no" in pushes[0][1] and pushes[0][2] == 1


def test_successful_job_sends_nothing(pushes):
    ss._run_safely("edgar_ingest", lambda: None)
    assert pushes == []


def test_a_broken_alert_never_breaks_the_job_runner(monkeypatch):
    def broken(*a, **k): raise OSError("network down")
    monkeypatch.setattr(alerts, "send_push", broken)
    def boom(): raise RuntimeError("x")
    ss._run_safely("edgar_ingest", boom)           # still must not raise


def test_missed_job_sends_a_push(pushes):
    ss._on_job_event(type("E", (), {"job_id": "form4_ingest"})())
    assert len(pushes) == 1 and "MISSED" in pushes[0][0] and "form4_ingest" in pushes[0][0]


def test_scheduler_listens_for_missed_jobs(monkeypatch):
    pytest.importorskip("apscheduler")
    from apscheduler.events import EVENT_JOB_MISSED
    monkeypatch.setenv("ENABLE_SCHEDULER", "1")
    ss._scheduler = None
    ss.start_scheduler()
    try:
        assert any(cb == ss._on_job_event and mask & EVENT_JOB_MISSED for cb, mask in ss._scheduler._listeners)
    finally:
        ss._scheduler.shutdown(wait=False); ss._scheduler = None


def test_send_push_does_nothing_without_keys(monkeypatch):
    monkeypatch.delenv("PUSHOVER_USER_KEY", raising=False); monkeypatch.delenv("PUSHOVER_APP_TOKEN", raising=False)
    called = []
    monkeypatch.setattr(alerts.urllib.request, "urlopen", lambda *a, **k: called.append(1))
    assert alerts.send_push("t", "m") is False and called == []


def test_send_push_posts_the_message_and_survives_network_errors(monkeypatch):
    monkeypatch.setenv("PUSHOVER_USER_KEY", "u"); monkeypatch.setenv("PUSHOVER_APP_TOKEN", "t")
    seen = []
    monkeypatch.setattr(alerts.urllib.request, "urlopen", lambda req, timeout=0: seen.append(req.data))
    assert alerts.send_push("Title", "Body") is True and b"Title" in seen[0] and b"priority=1" in seen[0]
    def down(*a, **k): raise OSError("down")
    monkeypatch.setattr(alerts.urllib.request, "urlopen", down)
    assert alerts.send_push("Title", "Body") is False
