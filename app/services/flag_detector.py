"""
Flag Detection Engine (v1).

Runs against unprocessed Filing rows and creates FlagEvent rows for
detected Tier-1 red flags. Built incrementally - each function below
handles one flag type. A Filing is only marked processed=True once
every flag check that applies to its form_type has run.

Currently implemented:
  - late_filing (NT 10-K / NT 10-Q): existence of the filing itself IS
    the flag, no content parsing required.

Not yet implemented (Filing left processed=False for these form types
until their detectors are built):
  - auditor_change, cfo_resignation, material_weakness (8-K item codes)
  - accelerated_insider_selling (Form 4, needs historical baseline)
"""
from app.db.session import SessionLocal
from app.models.filing import Filing, FlagEvent

HANDLED_FORM_TYPES = {"NT 10-K", "NT 10-Q"}


def detect_late_filing(filing: Filing) -> FlagEvent:
    return FlagEvent(
        filing_id=filing.id,
        cik=filing.cik,
        ticker=filing.ticker,
        flag_type="late_filing",
        flag_tier=1,
        filing_date=filing.filing_date,
        details={"form_type": filing.form_type},
    )


def run():
    db = SessionLocal()

    unprocessed = (
        db.query(Filing)
        .filter(Filing.processed.is_(False))
        .filter(Filing.form_type.in_(HANDLED_FORM_TYPES))
        .all()
    )

    flags_created = 0
    for filing in unprocessed:
        flag = detect_late_filing(filing)
        db.add(flag)
        filing.processed = True
        flags_created += 1

    db.commit()

    remaining_unhandled = (
        db.query(Filing)
        .filter(Filing.processed.is_(False))
        .count()
    )

    db.close()

    print(f"Filings checked (NT 10-K / NT 10-Q): {len(unprocessed)}")
    print(f"late_filing flags created: {flags_created}")
    print(f"Filings still unprocessed (awaiting 8-K/Form 4 detectors): {remaining_unhandled}")


if __name__ == "__main__":
    run()
