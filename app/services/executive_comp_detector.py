"""
Executive compensation red flag detection: Say-on-Pay vote failure
(8-K Item 5.07, "Submission of Matters to a Vote of Security Holders").
See decisions.md D-009 -- the last of the original 7 Category 1 flags.

Say-on-Pay approval below ~70% is a well-established governance-research
signal of real shareholder discontent with executive pay (ISS/Glass
Lewis and similar frameworks commonly use thresholds in this range).
Deliberately built around the actual VOTE NUMBERS (a real, verifiable
figure) rather than DEF 14A's compensation-discussion prose, to avoid
the entity-extraction/prose-judgment fragility that affected
related_party_change (D-014, disabled).

REVISED 2026-07-28 (v2): extraction logic verified against 8 REAL 8-K
filings pulled via live search (Micron, eBay, Eastman Chemical, Chevron,
A.H. Belo, AsiaInfo, Zoom Telephonics), PLUS two real MMM (3M) filings
found via a real database spot-check: MMM's actual 2024 say-on-pay
FAILURE (45.31% approval, shareholders explicitly "did not approve")
and its 2026 pass. The original symmetric 500/500-char search window
bled backward into an EARLIER, unrelated proposal (confirmed: V's
director-election vote percentage wrongly grabbed as if it were
say-on-pay data), and lacked support for the "labels-block-then-
numbers-block" table style (FOR/AGAINST/ABSTAIN listed together, THEN
all their numbers together in the same order) -- which caused MMM's
real 2024 failure to go completely undetected. Now uses a small
backward window (catches a table sitting just before its own confirming
mention, e.g. Eastman Chemical) and a larger forward window (the more
common case), plus a dedicated block-table pattern.
"""
import re
import time
import warnings

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from app.db.session import SessionLocal
from app.models.filing import Filing, FlagEvent
from app.models.quant_score import QuantScore  # noqa: F401 -- registers
# quant_scores in shared metadata so FlagEvent.quant_score_id's FK resolves

SEC_HEADERS = {"User-Agent": "Vijay Sentinel vijay.cloudarchitect@gmail.com"}
REQUEST_DELAY_SECONDS = 0.2

ITEM_507_RE = re.compile(r"item\s*5\.07", re.IGNORECASE)
SAYPAY_RE = re.compile(r"say[\s-]on[\s-]pay|advisory (?:vote|basis).{0,60}compensation", re.IGNORECASE)
FREQUENCY_RE = re.compile(r"frequency", re.IGNORECASE)
PERCENT_RE = re.compile(r"(\d{1,3}\.\d{1,2})\s*%")
NARRATIVE_RE = re.compile(
    r"([\d,]{4,})\s*(?:votes?\s*)?(?:in favor|for)\D{0,25}?([\d,]{4,})\s*(?:votes?\s*)?against",
    re.IGNORECASE,
)
TABLE_RE = re.compile(
    r"(?:(?i:votes?\s*for)|\bFor\b|\bFOR\b)\D{0,25}?([\d,]{4,})\D{0,40}?(?i:(?:votes?\s*)?against)\D{0,25}?([\d,]{4,})",
)
BLOCK_TABLE_RE = re.compile(
    r"\bFOR\s+AGAINST\s+ABSTAIN\b.{0,60}?([\d,]{4,})\s+([\d,]{4,})",
    re.DOTALL,
)

APPROVAL_THRESHOLD = 70.0  # below this = flagged as low say-on-pay support


def fetch_filing_text(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=SEC_HEADERS, timeout=20)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.content, "lxml")
            return soup.get_text(separator="\n")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"  WARN: fetch failed after {max_retries} attempts for {url}: {e}")
            return None


def find_sayonpay_approval_pct(text: str, before_window: int = 200, after_window: int = 800):
    """Returns (approval_pct, method) or (None, None). See module
    docstring for the v2 fix history."""
    for m in SAYPAY_RE.finditer(text):
        surrounding = text[max(0, m.start() - 100):m.start() + 150]
        if FREQUENCY_RE.search(surrounding):
            continue

        chunk = text[max(0, m.start() - before_window):m.start() + after_window]

        bm = BLOCK_TABLE_RE.search(chunk)
        if bm:
            for_votes, against_votes = int(bm.group(1).replace(",", "")), int(bm.group(2).replace(",", ""))
            total = for_votes + against_votes
            if total > 0:
                return round(100 * for_votes / total, 2), "block_table"

        pct_matches = PERCENT_RE.findall(chunk)
        if pct_matches:
            return float(pct_matches[0]), "percentage"

        nm = NARRATIVE_RE.search(chunk)
        if nm:
            for_votes, against_votes = int(nm.group(1).replace(",", "")), int(nm.group(2).replace(",", ""))
            total = for_votes + against_votes
            if total > 0:
                return round(100 * for_votes / total, 2), "narrative"

        tm = TABLE_RE.search(chunk)
        if tm:
            for_votes, against_votes = int(tm.group(1).replace(",", "")), int(tm.group(2).replace(",", ""))
            total = for_votes + against_votes
            if total > 0:
                return round(100 * for_votes / total, 2), "table"
    return None, None


def run(limit=None, rescan_all=False):
    db = SessionLocal()

    query = db.query(Filing).filter(Filing.form_type == "8-K")
    if not rescan_all:
        query = query.filter(Filing.processed.is_(False))
    query = query.order_by(Filing.id)  # deterministic
    if limit:
        query = query.limit(limit)
    filings = query.all()

    existing_flag_keys = {
        (fe.filing_id, fe.flag_type)
        for fe in db.query(FlagEvent.filing_id, FlagEvent.flag_type)
        .filter(FlagEvent.flag_type == "say_on_pay_failure").all()
    }

    flags_created = 0
    fetch_failures = 0
    no_item_507 = 0
    no_vote_data = 0

    for i, filing in enumerate(filings):
        try:
            if filing.raw_data and "full_text" in filing.raw_data:
                text = filing.raw_data["full_text"]
            elif filing.raw_data and "items" in filing.raw_data:
                text = " ".join(filing.raw_data["items"].values())
            else:
                text = fetch_filing_text(filing.filing_url)
                time.sleep(REQUEST_DELAY_SECONDS)
                if text is None:
                    fetch_failures += 1
                    continue
                if len(text) < 500_000:
                    existing_raw = filing.raw_data or {}
                    existing_raw["full_text"] = text
                    filing.raw_data = existing_raw

            if not ITEM_507_RE.search(text):
                no_item_507 += 1
                filing.processed = True
                continue

            pct, method = find_sayonpay_approval_pct(text)
            if pct is None:
                no_vote_data += 1
                filing.processed = True
                continue

            key = (filing.id, "say_on_pay_failure")
            if key not in existing_flag_keys and pct < APPROVAL_THRESHOLD:
                db.add(FlagEvent(
                    filing_id=filing.id,
                    source_type="disclosure",
                    cik=filing.cik,
                    ticker=filing.ticker,
                    flag_type="say_on_pay_failure",
                    flag_tier=1,
                    filing_date=filing.filing_date,
                    details={
                        "approval_pct": pct,
                        "extraction_method": method,
                        "threshold": APPROVAL_THRESHOLD,
                    },
                ))
                existing_flag_keys.add(key)
                flags_created += 1

            filing.processed = True
        except Exception as e:
            db.rollback()
            print(f"  WARN: unexpected error on filing {filing.id} ({filing.ticker}, {filing.filing_date}): {e}")
            continue

        if (i + 1) % 100 == 0:
            db.commit()
            print(f"  progress: {i + 1}/{len(filings)} filings checked, {flags_created} flags so far")

    db.commit()
    db.close()

    print(f"Filings checked: {len(filings)}")
    print(f"No Item 5.07 present (skipped): {no_item_507}")
    print(f"Item 5.07 present but no vote data extracted (skipped): {no_vote_data}")
    print(f"Fetch failures: {fetch_failures}")
    print(f"Flags created: {flags_created}")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    rescan_all = "--rescan-all" in sys.argv
    run(limit=limit, rescan_all=rescan_all)
