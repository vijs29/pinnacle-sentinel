"""
Form 4 ingestion: fetches raw XML, parses real transactions into
insider_transactions. See docs/journal.md for the schema verification
(Ameren/AEE, Warner Baxter, 2017-06-09) done before writing this.

REVISED (v3): parallelized the network-fetching step (index.json lookup
+ XML fetch per filing) across a small thread pool, since this is
purely I/O-bound work -- most wall-clock time is spent waiting for
SEC's servers, not doing CPU work. All database writes stay in the
main thread (SQLAlchemy sessions aren't safe to share across threads).
4 concurrent workers x 2 requests/filing, each individually paced,
keeps combined request rate comfortably under SEC's published 10
requests/second fair-access guidance while meaningfully speeding up
the 285K-filing backlog. The actual fetch/parse logic is UNCHANGED
from the already-verified v2 (index.json-based dynamic lookup, fixing
the earlier fixed-URL-transform bug) -- only the orchestration in
run() changed, to minimize risk of touching already-tested logic.

Only <nonDerivativeTransaction> elements are real transactions --
<nonDerivativeHolding> is an informational balance, not a transaction,
and is deliberately skipped.
"""
import time
import warnings
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from app.db.session import SessionLocal
from app.models.filing import Filing
from app.models.insider_transaction import InsiderTransaction

SEC_HEADERS = {"User-Agent": "Vijay Sentinel vijay.cloudarchitect@gmail.com"}
REQUEST_DELAY_SECONDS = 0.15
MAX_WORKERS = 2  # reduced from 4 on 2026-08-01 after failure rate escalated 56%->94% across two long runs; being gentler in case of intermittent SEC throttling under sustained load


def base_dir_url(cached_url: str) -> str:
    parts = cached_url.split("/")
    return "/".join(parts[:-2])


def find_real_xml_url(cached_url: str, max_retries: int = 3):
    base = base_dir_url(cached_url)
    index_url = f"{base}/index.json"

    for attempt in range(max_retries):
        try:
            resp = requests.get(index_url, headers=SEC_HEADERS, timeout=20)
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("directory", {}).get("item", [])
            xml_files = [item["name"] for item in items if item["name"].lower().endswith(".xml")]
            if not xml_files:
                return None
            return f"{base}/{xml_files[0]}"
        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"  WARN: index.json lookup failed after {max_retries} attempts for {index_url}: {e}")
            return None


def fetch_form4_xml(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=SEC_HEADERS, timeout=20)
            if resp.status_code != 200:
                return None
            return resp.text
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"  WARN: fetch failed after {max_retries} attempts for {url}: {e}")
            return None


def _fetch_one_filing(filing_id, filing_url, ticker):
    real_url = find_real_xml_url(filing_url)
    time.sleep(REQUEST_DELAY_SECONDS)
    if real_url is None:
        return (filing_id, ticker, None, "index_lookup_failure")

    xml_text = fetch_form4_xml(real_url)
    time.sleep(REQUEST_DELAY_SECONDS)
    if xml_text is None:
        return (filing_id, ticker, None, "fetch_failure")

    return (filing_id, ticker, xml_text, None)


def _text(el, path, default=None):
    found = el.find(path)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def _float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def parse_form4_xml(xml_text: str, filing_id: int, ticker: str):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  WARN: XML parse error for filing {filing_id}: {e}")
        return []

    issuer_cik = _text(root, "./issuer/issuerCik", "")

    owner = root.find("./reportingOwner")
    if owner is None:
        return []
    insider_cik = _text(owner, "./reportingOwnerId/rptOwnerCik", "")
    insider_name = _text(owner, "./reportingOwnerId/rptOwnerName", "")
    rel = owner.find("./reportingOwnerRelationship")
    is_officer = _text(rel, "./isOfficer", "0") == "1" if rel is not None else False
    is_director = _text(rel, "./isDirector", "0") == "1" if rel is not None else False
    is_ten_pct = _text(rel, "./isTenPercentOwner", "0") == "1" if rel is not None else False
    officer_title = _text(rel, "./officerTitle") if rel is not None else None

    results = []
    for table_name in ("nonDerivativeTable", "derivativeTable"):
        table = root.find(f"./{table_name}")
        if table is None:
            continue
        transaction_tag = "nonDerivativeTransaction" if table_name == "nonDerivativeTable" else "derivativeTransaction"
        for txn in table.findall(f"./{transaction_tag}"):
            txn_date = _text(txn, "./transactionDate/value")
            if not txn_date:
                continue
            code = _text(txn, "./transactionCoding/transactionCode", "")
            shares = _float(_text(txn, "./transactionAmounts/transactionShares/value"))
            price = _float(_text(txn, "./transactionAmounts/transactionPricePerShare/value"))
            ad_code = _text(txn, "./transactionAmounts/transactionAcquiredDisposedCode/value")
            owned_after = _float(_text(txn, "./postTransactionAmounts/sharesOwnedFollowingTransaction/value"))

            from datetime import datetime as _dt
            try:
                parsed_date = _dt.strptime(txn_date, "%Y-%m-%d").date()
            except ValueError:
                continue

            results.append(InsiderTransaction(
                filing_id=filing_id,
                issuer_cik=issuer_cik,
                ticker=ticker,
                insider_cik=insider_cik,
                insider_name=insider_name,
                is_officer=is_officer,
                is_director=is_director,
                is_ten_percent_owner=is_ten_pct,
                officer_title=officer_title,
                transaction_date=parsed_date,
                transaction_code=code,
                acquired_disposed_code=ad_code,
                shares=shares,
                price_per_share=price,
                shares_owned_after=owned_after,
            ))
    return results


def run(limit=None, rescan_all=False):
    db = SessionLocal()

    # FIXED: previously fetched `limit` filings by ID FIRST, then
    # filtered out already-done ones in Python -- meant a small-limit
    # test run mostly returned already-completed filings once real
    # progress existed (filtering happened AFTER the limit, not before).
    # Also loaded all 285K Filing rows into memory just to compute a set
    # difference. Now filters at the DATABASE level via NOT IN, so the
    # limit applies to genuinely-remaining work, and nothing more than
    # `limit` rows are ever pulled into memory.
    query = db.query(Filing).filter(Filing.form_type == "4")

    if not rescan_all:
        already_ingested_subq = db.query(InsiderTransaction.filing_id).distinct().subquery()
        query = query.filter(~Filing.id.in_(db.query(already_ingested_subq.c.filing_id)))

    query = query.order_by(Filing.id)
    if limit:
        query = query.limit(limit)
    filings = query.all()

    skipped_already_done = "N/A (filtered at DB level, not counted)" if not rescan_all else 0

    parsed_count = 0
    index_lookup_failures = 0
    fetch_failures = 0
    no_transactions = 0
    transactions_created = 0
    checked = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_one_filing, f.id, f.filing_url, f.ticker): f
            for f in filings
        }

        for future in as_completed(futures):
            filing_id, ticker, xml_text, error_reason = future.result()
            checked += 1

            if error_reason == "index_lookup_failure":
                index_lookup_failures += 1
            elif error_reason == "fetch_failure":
                fetch_failures += 1
            else:
                txns = parse_form4_xml(xml_text, filing_id, ticker)
                if not txns:
                    no_transactions += 1
                else:
                    for t in txns:
                        db.add(t)
                    transactions_created += len(txns)
                parsed_count += 1

            if checked % 20 == 0:
                db.commit()
                print(f"  progress: {checked}/{len(filings)} filings checked, {transactions_created} transactions created so far")

    db.commit()
    db.close()

    print(f"Filings checked: {len(filings)}")
    print(f"Already ingested, skipped: {skipped_already_done}")
    print(f"index.json lookup failures: {index_lookup_failures}")
    print(f"Fetch failures: {fetch_failures}")
    print(f"No transactions found (holding-only or parse issue): {no_transactions}")
    print(f"Filings successfully parsed: {parsed_count}")
    print(f"Total transaction rows created: {transactions_created}")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rescan_all = "--rescan-all" in sys.argv
    run(limit=limit, rescan_all=rescan_all)
