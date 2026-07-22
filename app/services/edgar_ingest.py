"""
EDGAR ingestion service (v1).

For each company in the universe, polls SEC's submissions API for recent
filings, filters to the 5 target form types, and writes new (not yet seen)
filings into the `filings` table with processed=False.

Flag detection (auditor change vs CFO resignation vs material weakness,
all of which share form type "8-K") happens in a separate downstream step
that inspects filing content - this stage only ingests raw metadata.
"""
import csv
import time
from datetime import datetime, date
from pathlib import Path

import requests

from app.db.session import SessionLocal
from app.models.filing import Filing

SEC_HEADERS = {"User-Agent": "Vijay Sentinel vijay.cloudarchitect@gmail.com"}
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

TARGET_FORMS = {"4", "8-K", "NT 10-K", "NT 10-Q"}

UNIVERSE_PATH = Path(__file__).resolve().parents[2] / "app" / "config" / "universe.csv"

# SEC allows up to 10 req/sec; stay comfortably under that
REQUEST_DELAY_SECONDS = 0.15


def load_universe() -> list[dict]:
    with open(UNIVERSE_PATH) as f:
        return list(csv.DictReader(f))


def fetch_submissions(cik: str) -> dict | None:
    url = SUBMISSIONS_URL.format(cik=cik)
    resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()


def parse_recent_filings(cik: str, ticker: str, company_name: str, data: dict) -> list[dict]:
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    report_dates = recent.get("reportDate", [])

    filings = []
    for i, form in enumerate(forms):
        if form not in TARGET_FORMS:
            continue
        accession_raw = accessions[i]
        accession_nodash = accession_raw.replace("-", "")
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession_nodash}/{primary_docs[i]}"
        )
        filings.append({
            "cik": cik,
            "company_name": company_name,
            "ticker": ticker,
            "form_type": form,
            "accession_number": accession_raw,
            "filing_date": datetime.strptime(dates[i], "%Y-%m-%d").date(),
            "period_of_report": (
                datetime.strptime(report_dates[i], "%Y-%m-%d").date()
                if report_dates[i] else None
            ),
            "filing_url": filing_url,
        })
    return filings


def ingest():
    universe = load_universe()
    db = SessionLocal()

    existing_accessions = {
        row.accession_number for row in db.query(Filing.accession_number).all()
    }

    total_seen = 0
    total_new = 0
    failed_ciks = []

    for row in universe:
        cik, ticker, company_name = row["cik"], row["ticker"], row["company_name"]
        data = fetch_submissions(cik)
        time.sleep(REQUEST_DELAY_SECONDS)

        if data is None:
            failed_ciks.append(cik)
            continue

        filings = parse_recent_filings(cik, ticker, company_name, data)
        total_seen += len(filings)

        for f in filings:
            if f["accession_number"] in existing_accessions:
                continue
            db.add(Filing(**f, processed=False))
            existing_accessions.add(f["accession_number"])
            total_new += 1

    db.commit()
    db.close()

    print(f"Companies polled: {len(universe)}")
    print(f"Failed lookups: {len(failed_ciks)}")
    print(f"Target-form filings seen (recent window): {total_seen}")
    print(f"New filings inserted: {total_new}")
    if failed_ciks:
        print(f"Sample failed CIKs: {failed_ciks[:10]}")


if __name__ == "__main__":
    ingest()
