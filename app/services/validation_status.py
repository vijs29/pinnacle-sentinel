"""Live numbers for the Flag Validation page: how many flags exist and how many have been graded.

Exact counts (never database estimates). A flag counts as graded once at least one of its outcome rows
has a graded_at timestamp. Stage 4 of the six-stage gauntlet needs 100+ graded live flags.
"""
from sqlalchemy import func

from app.models.filing import FlagEvent, SentinelOutcome

STAGE4_MIN_GRADED_FLAGS = 100


def validation_status(db):
    per_type = dict(
        db.query(FlagEvent.flag_type, func.count(FlagEvent.id)).group_by(FlagEvent.flag_type).all()
    )
    graded_flags = (
        db.query(func.count(func.distinct(SentinelOutcome.flag_event_id)))
        .filter(SentinelOutcome.graded_at.isnot(None))
        .scalar()
        or 0
    )
    return {
        "flags_detected": int(sum(per_type.values())),
        "flag_types_seen": len(per_type),
        "graded_flags": int(graded_flags),
        "stage4_required": STAGE4_MIN_GRADED_FLAGS,
        "stage4_reached": int(graded_flags) >= STAGE4_MIN_GRADED_FLAGS,
    }
