"""
Related-party transaction change detection (DEF 14A full-text,
year-over-year). See decisions.md D-009/D-010.

REWRITTEN 2026-07-28: the original version pulled from 10-K Item 13,
but for most large-cap filers Item 13 is just "incorporated by
reference" to the proxy statement -- an empty stub, not real content
(confirmed via spot-check: AWK, AIG, AMCR, MO, AEE all just said "see
our proxy statement"). The actual disclosure lives in the DEF 14A
(Item 404 of Regulation S-K, "Transactions with Related Persons").

Also rebuilt the entity-extraction logic after the first version's
naive "any capitalized phrase" approach caught debt-instrument names,
product names, and regulator names as false "related parties" (e.g.
MRK's own drug Keytruda, IDEXX's own product DecisionIQ, the EPA).
Now requires, WITHIN THE SAME SENTENCE: a name-shaped phrase, a dollar
figure, AND an explicit relationship word (son of/daughter of/spouse
of/beneficial owner/etc.) -- the combination genuine disclosures always
have and generic capitalized noise never does. Verified against 5
synthetic test cases (genuine 2025/2024 disclosures, an incorporate-by-
reference stub, debt-instrument noise, and a correct year-over-year
new-entity diff) before being applied here -- see journal.md.

Real-world SEC text will differ from these synthetic tests in ways not
yet seen -- this needs a real spot-check round, same as every other
detector today, before being fully trusted.
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

SECTION_HEADING_RE = re.compile(
    r"(related person transactions?|certain relationships and related (person )?transactions?|transactions with related persons?)",
    re.IGNORECASE,
)
RELATIONSHIP_WORDS_RE = re.compile(
    r"(son of|daughter of|spouse of|brother of|father of|mother of|father-in-law|mother-in-law|"
    r"immediate family|family member|beneficial owner|beneficially owns|5% stockholder|"
    r"significant stockholder|controlling stockholder)",
    re.IGNORECASE,
)
DOLLAR_RE = re.compile(r"\$[\d,]+")
NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+\b")
TITLE_STOPWORDS = {
    "Chief Executive", "Chief Financial", "Chief Operating", "Chief Legal",
    "Executive Officer", "Financial Officer", "Operating Officer", "Vice President",
    "Related Person", "Board Of", "Audit Committee",
    "Other Transactions", "Ordinary Course", "Compensation Committee",
    "Nominating Committee", "Governance Committee", "Named Executive",
    "We Describe", "Since The",
}
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

SECTION_MAX_CHARS = 8000


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


def extract_related_party_section(text: str):
    """Last occurrence of a REAL heading (capitalized in the source --
    real section headings render as standalone capitalized/Title-Case
    lines; lowercase mid-sentence matches are policy-paragraph references
    to the concept, not the actual disclosure section, e.g. CTSH's
    'related person transactions, we require each of our directors...'
    describing the approval PROCESS, not a real transaction), windowed
    to SECTION_MAX_CHARS after it."""
    matches = list(SECTION_HEADING_RE.finditer(text))
    real_headings = [m for m in matches if text[m.start()].isupper()]
    if not real_headings:
        return None
    m = real_headings[-1]
    return text[m.start():m.start() + SECTION_MAX_CHARS]


def extract_real_related_party_entities(section_text: str) -> set:
    heading_match = SECTION_HEADING_RE.search(section_text)
    body = section_text[heading_match.end():] if heading_match else section_text

    if not DOLLAR_RE.search(body) or not RELATIONSHIP_WORDS_RE.search(body):
        return set()  # no real transaction content -- boilerplate/stub

    result = set()
    for sentence in SENTENCE_SPLIT_RE.split(body):
        if not RELATIONSHIP_WORDS_RE.search(sentence):
            continue
        for name_match in NAME_RE.finditer(sentence):
            name = name_match.group(0)
            if name not in TITLE_STOPWORDS:
                result.add(name)
    return result


def find_prior_year_def14a(db, cik: str, current_filing_date):
    from datetime import timedelta
    candidates = (
        db.query(Filing)
        .filter(Filing.cik == cik, Filing.form_type == "DEF 14A")
        .filter(Filing.filing_date < current_filing_date)
        .filter(Filing.filing_date >= current_filing_date - timedelta(days=400))
        .filter(Filing.filing_date <= current_filing_date - timedelta(days=300))
        .order_by(Filing.filing_date.desc())
        .all()
    )
    return candidates[0] if candidates else None


def run(limit=None, rescan_all=False):
    db = SessionLocal()

    query = db.query(Filing).filter(Filing.form_type == "DEF 14A")
    if not rescan_all:
        query = query.filter(Filing.processed.is_(False))
    if limit:
        query = query.limit(limit)
    filings = query.all()

    existing_flag_keys = {
        (fe.filing_id, fe.flag_type)
        for fe in db.query(FlagEvent.filing_id, FlagEvent.flag_type)
        .filter(FlagEvent.flag_type == "related_party_change").all()
    }

    flags_created = 0
    fetch_failures = 0
    no_prior_year = 0
    no_section_found = 0
    no_real_content = 0

    for i, filing in enumerate(filings):
        try:
            prior_filing = find_prior_year_def14a(db, filing.cik, filing.filing_date)
            if prior_filing is None:
                no_prior_year += 1
                filing.processed = True
                continue

            if filing.raw_data and "full_text" in filing.raw_data:
                text = filing.raw_data["full_text"]
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

            if prior_filing.raw_data and "full_text" in prior_filing.raw_data:
                prior_text = prior_filing.raw_data["full_text"]
            else:
                prior_text = fetch_filing_text(prior_filing.filing_url)
                time.sleep(REQUEST_DELAY_SECONDS)
                if prior_text is None:
                    fetch_failures += 1
                    continue
                if len(prior_text) < 500_000:
                    existing_raw = prior_filing.raw_data or {}
                    existing_raw["full_text"] = prior_text
                    prior_filing.raw_data = existing_raw

            section = extract_related_party_section(text)
            prior_section = extract_related_party_section(prior_text)

            if section is None or prior_section is None:
                no_section_found += 1
                filing.processed = True
                continue

            entities = extract_real_related_party_entities(section)
            prior_entities = extract_real_related_party_entities(prior_section)

            if not entities and not prior_entities:
                no_real_content += 1
                filing.processed = True
                continue

            new_entities = entities - prior_entities

            key = (filing.id, "related_party_change")
            if key not in existing_flag_keys and new_entities:
                db.add(FlagEvent(
                    filing_id=filing.id,
                    source_type="disclosure",
                    cik=filing.cik,
                    ticker=filing.ticker,
                    flag_type="related_party_change",
                    flag_tier=1,
                    filing_date=filing.filing_date,
                    details={
                        "new_entities": sorted(new_entities)[:10],
                        "snippet": section[:600],
                    },
                ))
                existing_flag_keys.add(key)
                flags_created += 1

            filing.processed = True
        except Exception as e:
            db.rollback()
            print(f"  WARN: unexpected error on filing {filing.id} ({filing.ticker}, {filing.filing_date}): {e}")
            continue

        if (i + 1) % 50 == 0:
            db.commit()
            print(f"  progress: {i + 1}/{len(filings)} filings checked, {flags_created} flags so far")

    db.commit()
    db.close()

    print(f"Filings checked: {len(filings)}")
    print(f"No prior-year DEF 14A found (skipped): {no_prior_year}")
    print(f"No related-party section found (skipped): {no_section_found}")
    print(f"No real transaction content either year (skipped): {no_real_content}")
    print(f"Fetch failures: {fetch_failures}")
    print(f"Flags created: {flags_created}")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rescan_all = "--rescan-all" in sys.argv
    run(limit=limit, rescan_all=rescan_all)
