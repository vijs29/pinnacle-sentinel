"""
8-K Flag Detection (v1) — auditor_change, cfo_resignation, material_weakness,
financial_restatement, debt_covenant_violation.

Fetches each 8-K's document text, splits it into "Item X.XX" sections,
and classifies flags:

  Item 4.01 -> auditor_change (always; 4.01 is specifically the
              "Changes in Registrant's Certifying Accountant" item)
  Item 4.02 -> financial_restatement AND/OR material_weakness AND/OR
              auditor_change, checked INDEPENDENTLY (not elif -- FIXED
              2026-07-27, see classify_8k docstring)
  Item 2.04 -> debt_covenant_violation (always; "Triggering Events That
              Accelerate or Increase a Direct Financial Obligation" --
              existence of the item IS the flag)
  Item 5.02 -> cfo_resignation, only if item BODY text (boilerplate
              heading stripped first) mentions both a CFO role AND a
              resignation/departure keyword (5.02's standard heading
              always contains "departure"/"appointment" regardless of
              content, and would false-positive otherwise)

Rate-limited to stay well under SEC's request limits.
"""
import re
import subprocess
import time
import warnings
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from app.db.session import SessionLocal
from app.models.filing import Filing, FlagEvent
from app.models.quant_score import QuantScore  # noqa: F401 -- registers
# quant_scores in shared metadata so FlagEvent.quant_score_id's FK
# resolves at flush time (same bug hit in investigation_search.py and
# going_concern_detector.py earlier today -- missed applying it here
# until the live rescan started silently dropping financial_restatement
# and debt_covenant_violation flags, 2026-07-27)

SEC_HEADERS = {"User-Agent": "Vijay Sentinel vijay.cloudarchitect@gmail.com"}
REQUEST_DELAY_SECONDS = 0.2

NOTIFY_EVERY_N = 1000  # macOS notification popup interval (progress checkpoints)

def _notify(title: str, message: str):
    """Native macOS notification popup so progress is visible without
    checking the log file. Uses terminal-notifier (brew install
    terminal-notifier) rather than bare osascript -- found 2026-07-22 that
    Terminal.app doesn't reliably self-register with macOS Notification
    Center for osascript-triggered notifications, but terminal-notifier
    does register properly. Best-effort -- never lets a notification
    failure crash the actual job."""
    try:
        subprocess.run(
            ["terminal-notifier", "-title", title, "-message", message, "-sound", "default"],
            timeout=5, capture_output=True,
        )
    except Exception:
        pass

ITEM_HEADING_RE = re.compile(r"Item\s+(\d+\.\d+)\.?\s*([^\n]{0,120})", re.IGNORECASE)
ITEM_502_HEADING_RE = re.compile(r"^Item\s+5\.02\.?[^\n]*\n", re.IGNORECASE)

MATERIAL_WEAKNESS_KEYWORDS = ["material weakness", "internal control over financial reporting"]
AUDITOR_KEYWORDS = ["auditor", "accountant", "accounting firm", "pcaob", "engagement"]
CFO_KEYWORDS = ["chief financial officer", "cfo"]
RESIGNATION_KEYWORDS = ["resign", "resignation", "departure", "retire", "stepping down"]
RESTATEMENT_KEYWORDS = [
    "restate", "restatement", "non-reliance", "should no longer be relied upon",
    "previously issued financial statements", "erroneously",
]


def fetch_filing_text(url: str, max_retries: int = 3):
    """Fetch + parse a filing's text, with retry/backoff on transient
    network errors."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=SEC_HEADERS, timeout=20)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.content, "lxml")
            return soup.get_text(separator="\n")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            print(f"  WARN: fetch failed after {max_retries} attempts for {url}: {e}")
            return None


def extract_items(text: str) -> dict:
    matches = list(ITEM_HEADING_RE.finditer(text))
    items = {}
    for i, m in enumerate(matches):
        code = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        items[code] = text[start:end]
    return items


def _contains_any(text: str, keywords) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def classify_8k(items: dict) -> list:
    """FIXED 2026-07-27: Item 4.02 was previously an elif chain (material
    weakness OR auditor, first match wins) -- a pure restatement 8-K that
    mentioned neither set of keywords produced ZERO flags, silently. Item
    4.02 exists specifically to announce "Non-Reliance on Previously
    Issued Financial Statements" (a restatement) -- now checked
    independently from material_weakness and auditor_change, since a
    single filing can legitimately be all three at once. Confluence
    scoring wants these counted as genuinely separate signals."""
    flags = []

    if "4.01" in items:
        flags.append({
            "flag_type": "auditor_change",
            "item_code": "4.01",
            "snippet": items["4.01"][:500],
        })

    if "4.02" in items:
        text = items["4.02"]
        if _contains_any(text, RESTATEMENT_KEYWORDS):
            flags.append({"flag_type": "financial_restatement", "item_code": "4.02", "snippet": text[:500]})
        if _contains_any(text, MATERIAL_WEAKNESS_KEYWORDS):
            flags.append({"flag_type": "material_weakness", "item_code": "4.02", "snippet": text[:500]})
        if _contains_any(text, AUDITOR_KEYWORDS):
            flags.append({"flag_type": "auditor_change", "item_code": "4.02", "snippet": text[:500]})

    if "2.04" in items:
        # Debt covenant violation -- existence of this item IS the flag,
        # same pattern as late_filing (decisions.md D-009 Category 1 scope).
        flags.append({
            "flag_type": "debt_covenant_violation",
            "item_code": "2.04",
            "snippet": items["2.04"][:500],
        })

    if "5.02" in items:
        text = items["5.02"]
        body = ITEM_502_HEADING_RE.sub("", text, count=1)
        if _contains_any(body, CFO_KEYWORDS) and _contains_any(body, RESIGNATION_KEYWORDS):
            flags.append({"flag_type": "cfo_resignation", "item_code": "5.02", "snippet": body[:500]})

    return flags


def run(limit=None, rescan_all=False):
    """rescan_all=True: process ALL 8-Ks regardless of Filing.processed --
    needed when adding new flag types (financial_restatement,
    debt_covenant_violation, 2026-07-27) to backfill onto filings already
    scanned for the original three types. Dedups by (filing_id, flag_type)
    so this never creates a duplicate FlagEvent even when revisiting
    already-processed filings.

    Caches extracted item text into Filing.raw_data (the item sections
    dict, NOT full page text -- keeps storage bounded per decisions.md
    D-011's "extracted sections only" discipline) so a FUTURE flag-type
    addition can reuse already-fetched filings without a third full
    re-fetch from SEC."""
    db = SessionLocal()

    query = db.query(Filing).filter(Filing.form_type == "8-K")
    if not rescan_all:
        query = query.filter(Filing.processed.is_(False))
    if limit:
        query = query.limit(limit)
    filings = query.all()

    existing_flag_keys = {
        (fe.filing_id, fe.flag_type)
        for fe in db.query(FlagEvent.filing_id, FlagEvent.flag_type)
        .filter(FlagEvent.source_type == "disclosure").all()
    }

    flags_created = 0
    fetch_failures = 0
    other_failures = 0
    cache_hits = 0

    for i, filing in enumerate(filings):
        try:
            if filing.raw_data and "items" in filing.raw_data:
                items = filing.raw_data["items"]
                cache_hits += 1
            else:
                text = fetch_filing_text(filing.filing_url)
                time.sleep(REQUEST_DELAY_SECONDS)

                if text is None:
                    fetch_failures += 1
                    continue

                items = extract_items(text)
                filing.raw_data = {"items": items}

            detected = classify_8k(items)

            for d in detected:
                key = (filing.id, d["flag_type"])
                if key in existing_flag_keys:
                    continue
                db.add(FlagEvent(
                    filing_id=filing.id,
                    cik=filing.cik,
                    ticker=filing.ticker,
                    flag_type=d["flag_type"],
                    flag_tier=1,
                    filing_date=filing.filing_date,
                    details={"item_code": d["item_code"], "snippet": d["snippet"]},
                ))
                existing_flag_keys.add(key)
                flags_created += 1

            filing.processed = True
        except Exception as e:
            db.rollback()
            other_failures += 1
            print(f"  WARN: unexpected error on filing {filing.id} ({filing.ticker}, "
                  f"{filing.filing_date}): {e}")
            continue

        if (i + 1) % 100 == 0:
            db.commit()
            print(f"  progress: {i + 1}/{len(filings)} filings checked, {flags_created} flags so far")

        if (i + 1) % NOTIFY_EVERY_N == 0:
            remaining = len(filings) - (i + 1)
            _notify(
                "Sentinel 8-K Flag Detector",
                f"{i + 1}/{len(filings)} done, {remaining} remaining, {flags_created} flags so far"
            )

    db.commit()
    db.close()

    print(f"Filings checked: {len(filings)}")
    print(f"Cache hits (reused stored item text, no re-fetch): {cache_hits}")
    print(f"Fetch failures (left unprocessed, retry later): {fetch_failures}")
    print(f"Other failures (left unprocessed, retry later): {other_failures}")
    print(f"Flags created: {flags_created}")

    _notify("Sentinel 8-K Flag Detector", f"DONE -- {flags_created} flags created, {fetch_failures + other_failures} failures")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rescan_all = "--rescan-all" in sys.argv
    run(limit=limit, rescan_all=rescan_all)
