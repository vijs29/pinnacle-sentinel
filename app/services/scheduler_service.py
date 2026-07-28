"""Production scheduler -- automated EDGAR ingestion + flag detection jobs.

Enabled only when ENABLE_SCHEDULER=1 (set in production .env), matching
Pinnacle Quant's pattern exactly. Local dev keeps manual control by
default -- unattended laptops shouldn't be running long ingestion jobs
in the background.

All jobs use max_instances=1 -- this is also what prevents the exact
race condition found and fixed by hand on 2026-07-27 (two concurrent
going_concern_detector runs both deciding "no flag yet" before either
commit landed, producing duplicate flag_events rows). APScheduler's
max_instances=1 makes that structurally impossible for scheduled runs,
same discipline as the uq_filing_flag_type DB constraint added the
same day for manual/concurrent runs.

Schedule (all times ET, matching Quant's convention -- EDGAR filings
follow the same US market calendar even though Sentinel itself doesn't
need intraday precision):
  edgar_ingest         06:00 Mon-Fri -- pulls new 10-K/10-Q/8-K/4/DEF14A
                       metadata before the trading day starts
  flag_detector_8k     07:00 Mon-Fri -- rescans new 8-Ks for disclosure flags
  going_concern        07:30 Mon-Fri -- scans new 10-Ks
  investigation_search 08:00 Mon-Fri -- SEC full-text search sweep
  xbrl_ingest          Sunday 02:00 -- weekly, XBRL facts don't change intraday
  quant_scores         Sunday 03:00 -- weekly, depends on fresh XBRL facts
  quant_flags          Sunday 04:00 -- weekly, depends on fresh scores
"""
import logging
import os

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")
_scheduler = None


def _run_safely(name, fn, *args, **kwargs):
    logger.info(f"scheduler: {name} starting")
    try:
        fn(*args, **kwargs)
        logger.info(f"scheduler: {name} complete")
    except Exception as e:
        logger.error(f"scheduler: {name} failed: {e}")


def _edgar_ingest_job():
    from app.services.edgar_ingest import ingest
    _run_safely("edgar_ingest", ingest)


def _flag_detector_8k_job():
    from app.services.flag_detector_8k import run
    _run_safely("flag_detector_8k", run, limit=60000, rescan_all=False)


def _going_concern_job():
    from app.services.going_concern_detector import run
    _run_safely("going_concern", run, limit=5000, rescan_all=False)


def _investigation_search_job():
    from app.services.investigation_search import ingest
    from datetime import date, timedelta
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=7)).isoformat()
    _run_safely("investigation_search", ingest, start, end)


def _xbrl_ingest_job():
    from app.services.xbrl_ingest import ingest
    _run_safely("xbrl_ingest", ingest)


def _quant_scores_job():
    from app.services.quant_scores import compute_sloan_ratios, compute_beneish_m_scores, compute_altman_z_scores
    _run_safely("quant_scores (sloan)", compute_sloan_ratios)
    _run_safely("quant_scores (beneish)", compute_beneish_m_scores)
    _run_safely("quant_scores (altman)", compute_altman_z_scores)


def _quant_flags_job():
    from app.services.quant_flags import generate_quant_flags
    _run_safely("quant_flags", generate_quant_flags)


def start_scheduler() -> None:
    """Idempotent; call from FastAPI startup. No-op unless ENABLE_SCHEDULER=1."""
    global _scheduler
    if os.getenv("ENABLE_SCHEDULER", "0") != "1":
        logger.info("scheduler: disabled (set ENABLE_SCHEDULER=1 to enable)")
        return
    if _scheduler is not None:
        return

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    _scheduler = BackgroundScheduler(timezone=_ET)

    _scheduler.add_job(
        _edgar_ingest_job,
        CronTrigger(day_of_week="mon-fri", hour=6, minute=0, timezone=_ET),
        id="edgar_ingest", max_instances=1, coalesce=True, misfire_grace_time=1800,
    )
    _scheduler.add_job(
        _flag_detector_8k_job,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=0, timezone=_ET),
        id="flag_detector_8k", max_instances=1, coalesce=True, misfire_grace_time=1800,
    )
    _scheduler.add_job(
        _going_concern_job,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=30, timezone=_ET),
        id="going_concern", max_instances=1, coalesce=True, misfire_grace_time=1800,
    )
    _scheduler.add_job(
        _investigation_search_job,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone=_ET),
        id="investigation_search", max_instances=1, coalesce=True, misfire_grace_time=1800,
    )
    _scheduler.add_job(
        _xbrl_ingest_job,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=_ET),
        id="xbrl_ingest", max_instances=1, coalesce=True, misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _quant_scores_job,
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=_ET),
        id="quant_scores", max_instances=1, coalesce=True, misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _quant_flags_job,
        CronTrigger(day_of_week="sun", hour=4, minute=0, timezone=_ET),
        id="quant_flags", max_instances=1, coalesce=True, misfire_grace_time=3600,
    )

    _scheduler.start()
    for job in _scheduler.get_jobs():
        logger.info(f"scheduler: job {job.id:20s} next run {job.next_run_time}")


def scheduler_status() -> dict:
    if _scheduler is None:
        return {"enabled": False, "jobs": []}
    return {
        "enabled": True,
        "jobs": [
            {"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None}
            for j in _scheduler.get_jobs()
        ],
    }
