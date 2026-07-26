"""
XBRL financial-facts ingestion service (v1). See decisions.md D-009/D-010/D-011.

For each company in the universe, pulls SEC's companyfacts API (full
reported history, all fiscal years/periods available), filters to the
30-concept whitelist in app/config/xbrl_concepts.py, and writes new
(not yet seen) facts into the financial_facts table.

Whitelist is deliberately narrow -- expand app/config/xbrl_concepts.py
CONCEPTS as new ratios/scores need more line items. Re-running this
script after expanding the whitelist is safe: existing facts are
deduped via the unique constraint, only new (cik, concept, period)
combinations get inserted.
"""
import time

from datetime import datetime

import requests

from app.db.session import SessionLocal
from app.models.financial_fact import FinancialFact
from app.config.xbrl_concepts import CONCEPTS, INSTANT_CONCEPTS
from app.services.edgar_ingest import load_universe, SEC_HEADERS

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

REQUEST_DELAY_SECONDS = 0.15
MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 2, 4]
TIMEOUT_SECONDS = 20


def fetch_companyfacts(cik):
    """Fetch with retry/backoff, matching flag_detector_8k.py's resilience
    fix (2026-07-22/23) -- network errors retry up to 3x before giving up
    on this one company, never crashing the batch."""
    url = COMPANYFACTS_URL.format(cik=str(cik).zfill(10))
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=SEC_HEADERS, timeout=TIMEOUT_SECONDS)
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise requests.RequestException(f"status {resp.status_code}")
            return resp.json()
        except (requests.RequestException, requests.Timeout) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_SECONDS[attempt])
                continue
            print(f"  FAILED after {MAX_RETRIES} attempts: CIK {cik} ({e})")
            return None
    return None


def parse_facts(cik, ticker, data):
    """Extract whitelisted concepts from one company's companyfacts payload."""
    facts_out = []
    us_gaap = data.get("facts", {}).get("us-gaap", {})

    for concept in CONCEPTS:
        concept_data = us_gaap.get(concept)
        if not concept_data:
            continue

        for unit, entries in concept_data.get("units", {}).items():
            for entry in entries:
                end_date_raw = entry.get("end")
                if not end_date_raw:
                    continue
                end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
                start_date_raw = entry.get("start") if concept not in INSTANT_CONCEPTS else None
                start_date = (
                    datetime.strptime(start_date_raw, "%Y-%m-%d").date()
                    if start_date_raw else None
                )

                facts_out.append({
                    "cik": str(cik),
                    "ticker": ticker,
                    "concept": concept,
                    "unit": unit,
                    "start_date": start_date,
                    "end_date": end_date,
                    "fiscal_year": entry.get("fy"),
                    "fiscal_period": entry.get("fp"),
                    "form_type": entry.get("form"),
                    "value": entry.get("val"),
                    "accession_number": entry.get("accn"),
                })
    return facts_out


def ingest():
    universe = load_universe()
    db = SessionLocal()

    existing_keys = set()
    for r in db.query(
        FinancialFact.cik, FinancialFact.concept, FinancialFact.unit,
        FinancialFact.start_date, FinancialFact.end_date, FinancialFact.form_type,
    ).all():
        existing_keys.add((r[0], r[1], r[2], r[3], r[4], r[5]))

    total_companies = len(universe)
    total_facts_seen = 0
    total_new = 0
    failed_ciks = []

    for i, row in enumerate(universe, start=1):
        cik, ticker = row["cik"], row["ticker"]
        data = fetch_companyfacts(cik)
        time.sleep(REQUEST_DELAY_SECONDS)

        if data is None:
            failed_ciks.append(cik)
            continue

        try:
            facts = parse_facts(cik, ticker, data)
        except Exception as e:
            print(f"  PARSE ERROR: CIK {cik} ({e}) -- skipped, continuing")
            failed_ciks.append(cik)
            continue

        total_facts_seen += len(facts)

        for f in facts:
            key = (f["cik"], f["concept"], f["unit"], f["start_date"], f["end_date"], f["form_type"])
            if key in existing_keys:
                continue
            db.add(FinancialFact(**f))
            existing_keys.add(key)
            total_new += 1

        if i % 50 == 0:
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"  COMMIT ERROR at checkpoint {i}/{total_companies} -- rolled back this chunk, continuing ({e})")
            print(f"  progress: {i}/{total_companies} companies, {total_new} new facts so far")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  FINAL COMMIT ERROR -- rolled back last chunk ({e})")
    db.close()

    print(f"\nCompanies polled: {total_companies}")
    print(f"Failed lookups: {len(failed_ciks)}")
    print(f"Facts seen (whitelisted concepts): {total_facts_seen}")
    print(f"New facts inserted: {total_new}")
    if failed_ciks:
        print(f"Sample failed CIKs: {failed_ciks[:10]}")


if __name__ == "__main__":
    ingest()
