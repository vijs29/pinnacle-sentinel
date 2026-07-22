"""
8-K Flag Detection (v1) — auditor_change, cfo_resignation, material_weakness.

Fetches each unprocessed 8-K's document text, splits it into "Item X.XX"
sections, and classifies flags:

  Item 4.01 -> auditor_change (always; 4.01 is specifically the
              "Changes in Registrant's Certifying Accountant" item)
  Item 4.02 -> auditor_change OR material_weakness, decided by keyword
              match in the item text (4.02 covers both non-reliance
              restatements tied to auditor findings AND material
              weakness disclosures)
  Item 5.02 -> cfo_resignation, only if item BODY text (boilerplate
              heading stripped first) mentions both a CFO role AND a
              resignation/departure keyword (5.02's standard heading
              always contains "departure"/"appointment" regardless of
              content, and would false-positive otherwise)

Rate-limited to stay well under SEC's request limits.
"""
import re
import time
import requests
from bs4 import BeautifulSoup

from app.db.session import SessionLocal
from app.models.filing import Filing, FlagEvent

SEC_HEADERS = {"User-Agent": "Vijay Sentinel vijay.cloudarchitect@gmail.com"}
REQUEST_DELAY_SECONDS = 0.2

ITEM_HEADING_RE = re.compile(r"Item\s+(\d+\.\d+)\.?\s*([^\n]{0,120})", re.IGNORECASE)
ITEM_502_HEADING_RE = re.compile(r"^Item\s+5\.02\.?[^\n]*\n", re.IGNORECASE)

MATERIAL_WEAKNESS_KEYWORDS = ["material weakness", "internal control over financial reporting"]
AUDITOR_KEYWORDS = ["auditor", "accountant", "accounting firm", "pcaob", "engagement"]
CFO_KEYWORDS = ["chief financial officer", "cfo"]
RESIGNATION_KEYWORDS = ["resign", "resignation", "departure", "retire", "stepping down"]


def fetch_filing_text(url: str):
    resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.content, "lxml")
    return soup.get_text(separator="\n")


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
    flags = []

    if "4.01" in items:
        flags.append({
            "flag_type": "auditor_change",
            "item_code": "4.01",
            "snippet": items["4.01"][:500],
        })

    if "4.02" in items:
        text = items["4.02"]
        is_material_weakness = _contains_any(text, MATERIAL_WEAKNESS_KEYWORDS)
        is_auditor = _contains_any(text, AUDITOR_KEYWORDS)
        if is_material_weakness:
            flags.append({"flag_type": "material_weakness", "item_code": "4.02", "snippet": text[:500]})
        elif is_auditor:
            flags.append({"flag_type": "auditor_change", "item_code": "4.02", "snippet": text[:500]})

    if "5.02" in items:
        text = items["5.02"]
        # Strip the standard boilerplate heading before keyword matching --
        # it always contains "departure"/"appointment" regardless of actual
        # content, and would false-positive on almost every 5.02 filing.
        body = ITEM_502_HEADING_RE.sub("", text, count=1)
        if _contains_any(body, CFO_KEYWORDS) and _contains_any(body, RESIGNATION_KEYWORDS):
            flags.append({"flag_type": "cfo_resignation", "item_code": "5.02", "snippet": body[:500]})

    return flags


def run(limit=None):
    db = SessionLocal()

    query = (
        db.query(Filing)
        .filter(Filing.processed.is_(False))
        .filter(Filing.form_type == "8-K")
    )
    if limit:
        query = query.limit(limit)
    filings = query.all()

    flags_created = 0
    fetch_failures = 0

    for i, filing in enumerate(filings):
        text = fetch_filing_text(filing.filing_url)
        time.sleep(REQUEST_DELAY_SECONDS)

        if text is None:
            fetch_failures += 1
            continue

        items = extract_items(text)
        detected = classify_8k(items)

        for d in detected:
            db.add(FlagEvent(
                filing_id=filing.id,
                cik=filing.cik,
                ticker=filing.ticker,
                flag_type=d["flag_type"],
                flag_tier=1,
                filing_date=filing.filing_date,
                details={"item_code": d["item_code"], "snippet": d["snippet"]},
            ))
            flags_created += 1

        filing.processed = True

        if (i + 1) % 100 == 0:
            db.commit()
            print(f"  progress: {i + 1}/{len(filings)} filings checked, {flags_created} flags so far")

    db.commit()
    db.close()

    print(f"Filings checked: {len(filings)}")
    print(f"Fetch failures (left unprocessed, retry later): {fetch_failures}")
    print(f"Flags created: {flags_created}")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run(limit=limit)
