"""validation_status: exact counts of flags detected and flags graded."""
import os, sys
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.filing import Filing, FlagEvent, SentinelOutcome
from app.models.quant_score import QuantScore  # noqa: F401  (FlagEvent has a foreign key to it)
from app.services.validation_status import validation_status, STAGE4_MIN_GRADED_FLAGS


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Filing.__table__, QuantScore.__table__, FlagEvent.__table__, SentinelOutcome.__table__])
    return sessionmaker(bind=eng)()


def _flag(db, i, ftype="late_filing"):
    db.add(FlagEvent(id=i, cik="1", flag_type=ftype, filing_date=date(2026, 1, 1)))


def test_empty_database_reports_zeros():
    s = validation_status(_db())
    assert s == {"flags_detected": 0, "flag_types_seen": 0, "graded_flags": 0,
                 "stage4_required": STAGE4_MIN_GRADED_FLAGS, "stage4_reached": False}


def test_counts_flags_and_types():
    db = _db()
    for i, t in enumerate(["late_filing", "late_filing", "auditor_change"], start=1):
        _flag(db, i, t)
    db.commit()
    s = validation_status(db)
    assert s["flags_detected"] == 3 and s["flag_types_seen"] == 2


def test_only_graded_outcomes_count_and_each_flag_counts_once():
    db = _db()
    for i in (1, 2, 3):
        _flag(db, i)
    db.add_all([
        SentinelOutcome(flag_event_id=1, horizon_days=30, graded_at=datetime(2026, 11, 1)),
        SentinelOutcome(flag_event_id=1, horizon_days=90, graded_at=datetime(2026, 11, 1)),   # same flag, second horizon
        SentinelOutcome(flag_event_id=2, horizon_days=30, graded_at=None),                    # not graded yet
    ])
    db.commit()
    assert validation_status(db)["graded_flags"] == 1


def test_stage4_needs_the_full_minimum():
    db = _db()
    for i in range(1, STAGE4_MIN_GRADED_FLAGS + 1):
        _flag(db, i)
        db.add(SentinelOutcome(flag_event_id=i, horizon_days=30, graded_at=datetime(2026, 11, 1)))
    db.commit()
    assert validation_status(db)["stage4_reached"] is True
    db.query(SentinelOutcome).filter(SentinelOutcome.flag_event_id == 1).delete()
    db.commit()
    assert validation_status(db)["stage4_reached"] is False


def test_stage4_minimum_is_the_documented_100():
    # docs/METHODOLOGY.md, Six-Stage Gauntlet, stage 4: "Forward validation (100+ graded live flags)"
    assert STAGE4_MIN_GRADED_FLAGS == 100
