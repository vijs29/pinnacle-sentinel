"""
SEC EDGAR full-text search ingestion (v1). See decisions.md D-009/D-010.

Cross-company keyword scan via efts.sec.gov -- the right tool for
"which companies mention X" queries (unlike the per-company submissions
API used elsewhere in this project, D-005). Detects mentions of SEC
investigations, subpoenas, and whistleblower complaints in 10-K/10-Q/8-K
filings within our universe.

No local full-text storage needed -- this queries SEC's own search index
directly and stores only the matched filing metadata + a snippet.
"""
import time
import csv
from pathlib import Path

import requests

from app.db.session import SessionLocal
from app.models.filing import FlagEvent
from app.models.quant_score import QuantScore  # noqa: F401 -- import needed so
# SQLAlchemy registers the quant_scores table in shared metadata before
# resolving FlagEvent.quant_score_id's foreign key. Without this import,
# flushing a new FlagEvent raises NoReferencedTableError even though this
# script never touches QuantScore directly.

SEC_HEADERS = {"User-Agent": "Vijay Sentinel vijay.cloudarchitect@gmail.com"}
EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
REQUEST_DELAY_SECONDS = 0.3

UNIVERSE_PATH = Path(__file__).resolve().parents[2] / "app" / "config" / "universe.csv"

# Each entry: (search phrase, flag_type). Phrases are exact-match (quoted)
# per EFTS's phrase-search behavior -- deliberately specific phrasing to
# avoid false positives from routine boilerplate (e.g. "we may become
# subject to investigations" risk-factor language vs. an actual disclosed
# investigation).
INVESTIGATION_QUERIES = [
    ("received a subpoena", "sec_subpoena"),
    ("SEC investigation", "sec_investigation"),
    ("whistleblower complaint", "whistleblower_complaint"),
    ("formal order of investigation", "sec_investigation"),
]

TARGET_FORMS = "10-K,10-Q,8-K"


def load_universe_ciks_and_tickers() -> dict:
    """Returns {zero-padded cik: ticker}. FIXED 2026-07-27: EFTS responses
    don't include ticker at all -- display_names is formatted
    "Company Name  (CIK 0001329842)", not "(TICKER)" as originally
    assumed. Look up ticker from our own universe.csv instead."""
    with open(UNIVERSE_PATH) as f:
        return {row["cik"].zfill(10): row["ticker"] for row in csv.DictReader(f)}


def search_efts(query: str, forms: str, start_date: str, end_date: str, from_: int = 0, size: int = 10):
    params = {
        "q": f'"{query}"',
        "forms": forms,
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "from": from_,
        "size": size,
    }
    resp = requests.get(EFTS_URL, params=params, headers=SEC_HEADERS, timeout=20)
    if resp.status_code != 200:
        return None
    return resp.json()


def ingest(start_date: str, end_date: str):
    """start_date/end_date: 'YYYY-MM-DD'. Run incrementally (e.g. monthly)
    rather than backfilling the full 2001-present history in one call --
    EFTS caps total results at 10,000 per query and this is meant as an
    ongoing monitor, not a one-time historical backfill."""
    universe_ciks_tickers = load_universe_ciks_and_tickers()
    db = SessionLocal()

    existing_keys = {
        (fe.cik, fe.flag_type, fe.filing_date)
        for fe in db.query(FlagEvent.cik, FlagEvent.flag_type, FlagEvent.filing_date)
        .filter(FlagEvent.flag_type.in_([ft for _, ft in INVESTIGATION_QUERIES]))
        .all()
    }

    total_hits_seen = 0
    total_in_universe = 0
    flags_created = 0

    for phrase, flag_type in INVESTIGATION_QUERIES:
        data = search_efts(phrase, TARGET_FORMS, start_date, end_date)
        time.sleep(REQUEST_DELAY_SECONDS)

        if data is None:
            print(f"  WARN: search failed for phrase '{phrase}'")
            continue

        hits = data.get("hits", {}).get("hits", [])
        total_hits_seen += len(hits)

        for hit in hits:
            source = hit.get("_source", {})
            # FIXED 2026-07-27: real EFTS response uses "ciks" (plural,
            # array) and "root_forms" (plural, array) -- NOT "cik"/
            # "root_form" singular as originally assumed. The singular
            # forms silently returned None every time, meaning this
            # would have filtered out 100% of results without erroring.
            ciks_list = source.get("ciks", [])
            if not ciks_list:
                continue
            cik = str(ciks_list[0]).zfill(10)

            if cik not in universe_ciks_tickers:
                continue
            total_in_universe += 1

            file_date = source.get("file_date")
            if not file_date:
                continue

            key = (cik, flag_type, file_date)
            if key in existing_keys:
                continue

            ticker = universe_ciks_tickers.get(cik)
            form_types = source.get("root_forms") or [source.get("form")]

            db.add(FlagEvent(
                filing_id=None,
                source_type="disclosure",
                cik=cik,
                ticker=ticker,
                flag_type=flag_type,
                flag_tier=2,  # these are inherently higher-severity than routine disclosure flags
                filing_date=file_date,
                details={
                    "matched_phrase": phrase,
                    "accession_number": source.get("adsh"),
                    "form_type": form_types[0] if form_types else None,
                    "display_names": source.get("display_names", []),
                },
            ))
            existing_keys.add(key)
            flags_created += 1

    db.commit()
    db.close()

    print(f"Queries run: {len(INVESTIGATION_QUERIES)}")
    print(f"Total hits seen (all companies, not just universe): {total_hits_seen}")
    print(f"Hits within our 503-company universe: {total_in_universe}")
    print(f"New flags created: {flags_created}")


if __name__ == "__main__":
    import sys
    start = sys.argv[1] if len(sys.argv) > 1 else "2025-01-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2025-12-31"
    ingest(start, end)
