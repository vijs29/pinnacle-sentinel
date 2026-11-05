"""form4_ingest must work through the NEWEST filings first (recent data matters most)."""
import os, sys
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.filing import Filing
from app.models.insider_transaction import InsiderTransaction  # noqa: F401
from app.services import form4_ingest


def test_run_fetches_newest_filings_first(monkeypatch):
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Filing.__table__, InsiderTransaction.__table__])
    S = sessionmaker(bind=eng)
    db = S()
    for i, d in enumerate([date(2020, 1, 1), date(2026, 11, 3), date(2023, 5, 5)], start=1):
        db.add(Filing(id=i, cik="1", company_name="C", ticker="T", form_type="4",
                      accession_number=f"A{i}", filing_date=d, filing_url=f"u{i}", processed=False))
    db.commit(); db.close()

    seen = []
    monkeypatch.setattr(form4_ingest, "SessionLocal", S)
    monkeypatch.setattr(form4_ingest, "_fetch_one_filing",
                        lambda fid, url, t: (seen.append(fid) or (fid, t, None, "fetch_failure")))
    monkeypatch.setattr(form4_ingest, "MAX_WORKERS", 1)
    form4_ingest.run(limit=2, rescan_all=False)
    assert sorted(seen) == [2, 3]          # only the two newest (2026-11-03, 2023-05-05)
