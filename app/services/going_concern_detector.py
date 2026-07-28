"""
Going-concern language detection (10-K full-text). See decisions.md
D-009/D-010/D-011.

Unlike 8-K's clean "Item X.XX" structure, 10-Ks have no standardized
machine-parseable section headers for the audit opinion -- filers title
it differently ("Report of Independent Registered Public Accounting
Firm", "Independent Auditor's Report", etc.). Rather than try to isolate
that section, this searches the ENTIRE filing text directly for the
standard PCAOB/AICPA going-concern phrasing, which is specific and rare
enough that a false positive elsewhere in the document is very unlikely.

Reuses the same architecture as flag_detector_8k.py: fetch, cache
extracted text into Filing.raw_data (not the full document -- keeps
storage bounded per D-011), dedup by (filing_id, flag_type), rescan-safe.
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
# quant_scores in shared metadata so FlagEvent.quant_score_id's FK
# resolves at flush time (same fix as investigation_search.py, 2026-07-27)

SEC_HEADERS = {"User-Agent": "Vijay Sentinel vijay.cloudarchitect@gmail.com"}
REQUEST_DELAY_SECONDS = 0.2

# Standard PCAOB/AICPA going-concern qualification phrasing. Deliberately
# specific -- these are near-verbatim phrases auditors use, not generic
# words that would false-positive on routine risk-factor boilerplate.
GOING_CONCERN_PATTERNS = [
    re.compile(r"substantial doubt.{0,80}ability.{0,40}continue as a going concern", re.IGNORECASE | re.DOTALL),
    re.compile(r"ability.{0,40}(?:company|corporation|entity).{0,40}continue as a going concern", re.IGNORECASE | re.DOTALL),
    re.compile(r"raise substantial doubt", re.IGNORECASE),
]

SNIPPET_CONTEXT_CHARS = 400  # characters of surrounding context to store per match


def fetch_filing_text(url: str, max_retries: int = 3):
    """Same retry/backoff pattern as flag_detector_8k.py."""
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


# FIXED 2026-07-27, found via spot-check of the 91 initial flags (journal.md):
# two real false-positive classes existed in the original phrase-only match.
# (1) Boilerplate: "Management evaluates ... whether there are conditions
#     ... that raise substantial doubt" is ROUTINE risk-assessment-policy
#     language required in every 10-K's footnotes -- describes the ONGOING
#     EVALUATION PROCESS, not an actual finding. Confirmed via WTW (5 of 91
#     flags, identical boilerplate every year).
# (2) Third-party: "the substantial doubt about Canopy's ability to
#     continue as a going concern, as disclosed by Canopy" -- the FILER
#     disclosing a DIFFERENT company's (an investee's) going-concern
#     doubt, not its own. Confirmed via STZ (Canopy investee) and WAT
#     (unnamed investee), 6 of 91 flags combined.
# Both patterns use nearly identical core phrasing to a genuine finding
# (confirmed true positive: ECHO, "which raises substantial doubt about
# our ... ability to continue as a going concern" -- first-person,
# declarative, no hedging or third-party language) -- phrase matching
# alone cannot distinguish them; these two exclusion checks can.
# REVISED 2026-07-27 (v2): the first fix (BOILERPLATE_RE requiring the
# exact word "evaluates") missed a huge class of the SAME false-positive
# pattern using other verb forms -- "requires management to EVALUATE
# whether", "responsibility in EVALUATING whether" -- both common in the
# routine 2016-2017 ASU 2014-15 standard-adoption footnote nearly every
# S&P 500 company carries. Broadened to match any evaluat(e|es|ed|ing).
#
# Also revised third-party detection: a blanket "its/their ability to
# continue" exclusion over-corrected -- "its" is exactly as likely to be
# genuinely self-referential ("the Company... raised substantial doubt
# about ITS ability", i.e. the filer's own finding) as it is to refer to
# a different named entity ("Genesis indicated... THEIR ability", a
# tenant/investee, not the filer). Pronouns alone can't disambiguate this.
# Now requires a distinct capitalized entity name to be the actual
# grammatical subject of a disclosure verb (indicated/disclosed/stated/
# reported/concluded) shortly before the doubt language -- catches
# "Genesis indicated..." and "Bakkt has subsequently disclosed..." while
# correctly keeping "The Company's... raised doubt about its ability"
# (self-reference words like "The"/"Company"/"Management" excluded from
# counting as a real third-party subject).
# REVISED 2026-07-27 (v3): v2's heuristic third-party detection (a
# blanket "different capitalized name = third party" check) failed on
# real cases where a company refers to ITSELF by full legal name rather
# than "the Company"/"our" -- e.g. PG&E's own 10-K says "substantial
# doubt about PG&E Corporation's ... ability to continue", which looks
# identical in structure to a genuine third-party reference like
# "Canopy's ability to continue". No amount of additional regex
# heuristics can distinguish these reliably -- v2 also broke on PG&E's
# actual phrasing ("PG&E Corporation's AND the Utility's ability to
# continue", two possessives joined by "and", where the regex grabbed
# the wrong one). Also missed CRL's "assess IF" phrasing (v1/v2 only
# matched "whether").
#
# v3 uses the one piece of ground-truth data actually available: the
# filing's own real company name (Filing.company_name). Rather than
# guess whether a matched name is self-referential, check whether the
# filer's own name appears anywhere in the text window leading up to
# "ability to continue" -- if it does, the filer is naming itself
# (however it phrases that), not excluded as third-party. This resolves
# the ambiguity with real data instead of more pattern heuristics.
# Verified against all 12 real cases found during this investigation
# (STZ/Canopy, WAT/investee, WTW, CRL, ECHO x2, EXE, PCG x2, ICE/Bakkt,
# WELL/Genesis, AFL) before being applied here -- see journal.md.
# REVISED 2026-07-27 (v4): still more boilerplate variants found after v3
# (ACGL: "require management to assess an entity's ability ... by
# incorporating", cites Subtopic 205-40 explicitly; BLDR: "perform ...
# assessments on whether", a noun form neither v1-v3 caught). Rather than
# keep chasing individual verb/noun forms indefinitely, combined two
# signals: (1) explicit citation of the accounting standard itself (ASU
# 2014-15 / Subtopic 205-40 / "FASB issued") -- every false positive
# found describes the STANDARD, no genuine finding ever does; (2) the
# broader "requires management to / evaluates|assesses ... whether|if"
# policy-description phrasing, now including the "assessments on
# whether" noun-form variant. Verified against all 9 real false/true
# positive cases found during this investigation before landing here.
BOILERPLATE_RE = re.compile(
    r"(ASU\s*2014-15|Subtopic\s*205-40|FASB\s+issued|"
    r"requires\s+management\s+to\s+(assess|evaluat|perform).{0,150}(whether|\bif\b)|"
    r"(evaluat|assess)(e|es|ed|ing)?.{0,250}(whether|\bif\b)|"
    r"assessments?\s+(on|of|regarding)\s+whether)",
    re.IGNORECASE | re.DOTALL
)
INVESTEE_RE = re.compile(r"(as disclosed by|the investee.?s\s+ability)", re.IGNORECASE)
POSSESSIVE_RE = re.compile(r"[A-Z][a-zA-Z&]+(?:'s|.s)\s+(?:and\s+(?:the\s+)?[A-Z][a-zA-Z&]+(?:'s|.s)\s+)?ability\s+to\s+continue")
NAMED_DISCLOSURE_RE = re.compile(
    r"([A-Z][a-zA-Z]+)\s+(?:has\s+|had\s+)?(?:\w+\s+){0,2}(indicated|disclosed|stated|reported|concluded)",
)
SELF_REFERENCE_WORDS = {"The", "Company", "Management", "Registrant", "Circumstances", "These"}


def _normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"^\s*the\s+", "", name)
    name = re.sub(r"[.,&]", " ", name)
    for suffix in ["corporation", "corp", "incorporated", "inc", "company", "co", "ltd", "limited", "group", "holdings", "plc", "llc"]:
        name = re.sub(r"\b" + suffix + r"\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def _is_third_party(snippet: str, company_name: str) -> bool:
    if INVESTEE_RE.search(snippet):
        return True

    filer_word = _normalize_name(company_name).split()[0] if company_name and _normalize_name(company_name) else ""

    m = re.search(r"ability\s+to\s+continue", snippet)
    if m:
        window = snippet[max(0, m.start() - 200):m.start()].lower()
        filer_named_here = bool(filer_word) and filer_word in window
        if POSSESSIVE_RE.search(snippet) and not filer_named_here:
            return True

    m2 = NAMED_DISCLOSURE_RE.search(snippet)
    if m2:
        name = m2.group(1)
        if name not in SELF_REFERENCE_WORDS and _normalize_name(name) != filer_word:
            return True
    return False


def find_going_concern_snippet(text: str, company_name: str = ""):
    """Returns the matched phrase + surrounding context, or None. Excludes
    boilerplate risk-assessment-policy language and third-party/investee
    references by comparing against the filer's own real company name --
    see comments above."""
    for pattern in GOING_CONCERN_PATTERNS:
        m = pattern.search(text)
        if m:
            start = max(0, m.start() - SNIPPET_CONTEXT_CHARS // 2)
            end = min(len(text), m.end() + SNIPPET_CONTEXT_CHARS // 2)
            snippet = text[start:end].strip()
            if BOILERPLATE_RE.search(snippet) or _is_third_party(snippet, company_name):
                continue  # try the next pattern rather than accept a known false-positive class
            return snippet
    return None


def run(limit=None, rescan_all=False):
    db = SessionLocal()

    query = db.query(Filing).filter(Filing.form_type == "10-K")
    if not rescan_all:
        query = query.filter(Filing.processed.is_(False))
    if limit:
        query = query.limit(limit)
    filings = query.all()

    existing_flag_keys = {
        (fe.filing_id, fe.flag_type)
        for fe in db.query(FlagEvent.filing_id, FlagEvent.flag_type)
        .filter(FlagEvent.flag_type == "going_concern").all()
    }

    flags_created = 0
    fetch_failures = 0
    other_failures = 0
    cache_hits = 0

    for i, filing in enumerate(filings):
        try:
            if filing.raw_data and "full_text" in filing.raw_data:
                text = filing.raw_data["full_text"]
                cache_hits += 1
            else:
                text = fetch_filing_text(filing.filing_url)
                time.sleep(REQUEST_DELAY_SECONDS)
                if text is None:
                    fetch_failures += 1
                    continue
                # Cache only if reasonably sized -- 10-Ks can be huge;
                # storing the full doc for every one of 503 companies x
                # years would violate D-011's "extracted sections only"
                # storage discipline. Skip caching text over ~500KB;
                # future re-runs just re-fetch those (acceptable cost,
                # rare case -- most 10-Ks are well under this).
                if len(text) < 500_000:
                    existing_raw = filing.raw_data or {}
                    existing_raw["full_text"] = text
                    filing.raw_data = existing_raw

            key = (filing.id, "going_concern")
            if key not in existing_flag_keys:
                snippet = find_going_concern_snippet(text, filing.company_name)
                if snippet:
                    db.add(FlagEvent(
                        filing_id=filing.id,
                        source_type="disclosure",
                        cik=filing.cik,
                        ticker=filing.ticker,
                        flag_type="going_concern",
                        flag_tier=2,  # going-concern is a severe, well-established signal
                        filing_date=filing.filing_date,
                        details={"snippet": snippet},
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

        if (i + 1) % 50 == 0:
            db.commit()
            print(f"  progress: {i + 1}/{len(filings)} filings checked, {flags_created} flags so far")

    db.commit()
    db.close()

    print(f"Filings checked: {len(filings)}")
    print(f"Cache hits (reused stored text, no re-fetch): {cache_hits}")
    print(f"Fetch failures (left unprocessed, retry later): {fetch_failures}")
    print(f"Other failures (left unprocessed, retry later): {other_failures}")
    print(f"Flags created: {flags_created}")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rescan_all = "--rescan-all" in sys.argv
    run(limit=limit, rescan_all=rescan_all)
