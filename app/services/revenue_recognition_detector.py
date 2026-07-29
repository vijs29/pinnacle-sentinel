"""
Revenue-recognition policy change detection (10-K full-text,
year-over-year). See decisions.md D-009.

Unlike related_party_change (D-014, disabled -- entity extraction proved
unreliable), this detects a CHANGE IN SUBSTANCE via word-overlap
similarity between this year's and last year's "Revenue Recognition"
accounting-policy note, rather than trying to extract discrete named
entities. Verified against a real filing (Devon Energy's 10-K) before
building: the heading renders as a standalone capitalized line (same
"last occurrence, must be capitalized" fix that worked for going-concern
and the eventual related-party attempt), the policy note is long
(multiple sub-headings -- Upstream Revenues, Oil sales, etc.), and real
SEC text-to-HTML conversion injects page-break boilerplate mid-paragraph
("54 Table of Contents... NOTES TO CONSOLIDATED FINANCIAL STATEMENTS --
(Continued)"). Word-overlap similarity is more robust to this noise than
entity extraction was: if the same boilerplate appears in both years
(routine), it inflates similarity for BOTH years equally, biasing
toward "looks unchanged" (a false negative) rather than a false alarm --
a safer failure mode than related_party_change's false positives.
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

SECTION_HEADING_RE = re.compile(r"revenue recognition", re.IGNORECASE)
SECTION_MAX_CHARS = 6000  # widened after seeing DVN's real multi-subsection note

STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "and", "or", "in", "on", "for",
    "we", "our", "company", "that", "this", "as", "be", "with", "when", "at",
    "by", "from", "which", "such", "any", "all", "will", "not", "if", "it",
    "revenue", "recognition", "recognize", "recognized", "recognizes",
    "table", "contents", "index", "financial", "statements", "notes",
    "consolidated", "continued", "subsidiaries",
}
WORD_RE = re.compile(r"[a-z]+")

SIMILARITY_THRESHOLD = 0.5  # below this = flagged as materially changed


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


def _digit_density(text: str) -> float:
    digits = sum(c.isdigit() for c in text)
    alpha = sum(c.isalpha() for c in text)
    total = digits + alpha
    return digits / total if total else 1.0  # empty/non-alnum text treated as maximally suspicious


def extract_revenue_recognition_section(text: str, min_significant_words: int = 10, check_window_chars: int = 500, max_digit_density: float = 0.15):
    """FIXED 2026-07-28 (v3): word-count density (both wide-window and
    narrow-window versions) proved unreliable -- real deferred-tax
    reconciliation tables have MANY rows, each with a legitimate
    multi-syllable English label ("liabilities", "deferred",
    "compensation"), so word-counting alone cannot distinguish a table
    from prose no matter the window size (confirmed: ACN 2025 still
    passed the narrow-window word check). Switched to DIGIT DENSITY --
    a structurally different signal (grammar vs. numeric table), not
    another word-counting variant. Verified against the exact real ACN
    snippets: genuine prose measured 0.055 digit density, the tax-table
    false match measured 0.391 -- nearly 7x separation, comfortably
    either side of the 0.15 threshold."""
    matches = list(SECTION_HEADING_RE.finditer(text))
    real_headings = [m for m in matches if text[m.start()].isupper()]
    for m in reversed(real_headings):
        check_window = text[m.start():m.start() + check_window_chars]
        if (len(significant_words(check_window)) >= min_significant_words
                and _digit_density(check_window) <= max_digit_density):
            return text[m.start():m.start() + SECTION_MAX_CHARS]
    return None


def significant_words(text: str) -> set:
    words = WORD_RE.findall(text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 3}


def jaccard_similarity(text_a: str, text_b: str):
    a, b = significant_words(text_a), significant_words(text_b)
    if not a or not b:
        return None
    return len(a & b) / len(a | b)


def find_prior_year_10k(db, cik: str, current_filing_date):
    from datetime import timedelta
    candidates = (
        db.query(Filing)
        .filter(Filing.cik == cik, Filing.form_type == "10-K")
        .filter(Filing.filing_date < current_filing_date)
        .filter(Filing.filing_date >= current_filing_date - timedelta(days=400))
        .filter(Filing.filing_date <= current_filing_date - timedelta(days=330))
        .order_by(Filing.filing_date.desc())
        .all()
    )
    return candidates[0] if candidates else None


def run(limit=None, rescan_all=False):
    db = SessionLocal()

    query = db.query(Filing).filter(Filing.form_type == "10-K")
    if not rescan_all:
        query = query.filter(Filing.processed.is_(False))
    query = query.order_by(Filing.id)  # deterministic -- learned this
    # lesson from related_party_detector.py's test-run ordering bug
    if limit:
        query = query.limit(limit)
    filings = query.all()

    existing_flag_keys = {
        (fe.filing_id, fe.flag_type)
        for fe in db.query(FlagEvent.filing_id, FlagEvent.flag_type)
        .filter(FlagEvent.flag_type == "revenue_recognition_change").all()
    }

    flags_created = 0
    fetch_failures = 0
    no_prior_year = 0
    no_section_found = 0

    for i, filing in enumerate(filings):
        try:
            prior_filing = find_prior_year_10k(db, filing.cik, filing.filing_date)
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

            section = extract_revenue_recognition_section(text)
            prior_section = extract_revenue_recognition_section(prior_text)

            if section is None or prior_section is None:
                no_section_found += 1
                filing.processed = True
                continue

            similarity = jaccard_similarity(section, prior_section)
            if similarity is None:
                no_section_found += 1
                filing.processed = True
                continue

            key = (filing.id, "revenue_recognition_change")
            if key not in existing_flag_keys and similarity < SIMILARITY_THRESHOLD:
                db.add(FlagEvent(
                    filing_id=filing.id,
                    source_type="disclosure",
                    cik=filing.cik,
                    ticker=filing.ticker,
                    flag_type="revenue_recognition_change",
                    flag_tier=1,
                    filing_date=filing.filing_date,
                    details={
                        "similarity_score": round(similarity, 3),
                        "this_year_snippet": section[:600],
                        "prior_year_snippet": prior_section[:600],
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
    print(f"No prior-year 10-K found (skipped): {no_prior_year}")
    print(f"No section found either year (skipped): {no_section_found}")
    print(f"Fetch failures: {fetch_failures}")
    print(f"Flags created: {flags_created}")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rescan_all = "--rescan-all" in sys.argv
    run(limit=limit, rescan_all=rescan_all)
