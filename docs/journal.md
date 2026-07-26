# Pinnacle Sentinel — Journal

> Running chronological log of what was actually done, decided, and learned.
> Facts and real outputs only -- never fabricated numbers. Newest entry last
> (unlike Pinnacle Quant's JOURNAL.md, which is newest-first -- Sentinel
> follows Veridia's chronological convention instead).

---

## 2026-07-20 -- Project scaffolding

Scoped the product: SEC filings monitoring, 5 Tier-1 structured red flags,
confluence scoring, eventual outcome validation (see decisions.md D-001
through D-004, strategy.md for the full thesis).

Built:
- FastAPI backend scaffold (port 8010), Postgres database `pinnacle_sentinel`.
- SQLAlchemy models: initially a flat single-table `Filing` design (later
  superseded, see D-007) with confluence_score/flag_type/outcome columns
  directly on the row.
- React/Vite frontend scaffold (port 5180), `App.jsx` routing to
  `Landing`/`Screener` pages (neither page's actual component was written
  yet -- still true as of this entry).
- CORS configured for the frontend port.

## 2026-07-21 -- Universe, EDGAR ingestion, first two flag detectors, schema redesign

**Universe builder.** Attempted Russell 1000 via iShares IWB holdings CSV
first -- blocked by Akamai Bot Manager (confirmed via bm_s/bm_so/bm_ss
cookies after several escalating attempts: bare request, browser User-Agent,
session-cookie warmup via product-page visit first). Pivoted to S&P 500
via Wikipedia's constituent table -- clean, static HTML, includes CIK
directly. Hit a pandas 3.0.3 `read_html` filename-vs-literal-HTML bug
(needed `io.StringIO(resp.text)` instead of passing the raw string
directly) -- fixed, then successfully parsed 503 constituents.
`app/services/universe_builder.py`, output `app/config/universe.csv`.
Weekly auto-refresh deferred until an ingestion scheduler exists (still
deferred as of this entry).

**Schema redesign (D-007).** Replaced the original flat `Filing` table
with three normalized tables: `Filing` (raw metadata), `FlagEvent` (one row
per detected flag), `SentinelOutcome` (grading per flag per horizon,
schema built, not yet populated), plus `WatchlistItem`. Old flat table
dropped from local Postgres (confirmed empty first, no data loss).

**EDGAR ingestion.** `app/services/edgar_ingest.py`, polling SEC's
submissions API (D-005) for all 503 universe companies across 4 target
form types (Form 4, 8-K, NT 10-K, NT 10-Q). First full run: **342,429
filings ingested** -- higher than expected because the submissions API's
"recent" block returns each company's FULL available history (capped
~1000 entries per company), not just recent activity, so this was
effectively a full historical backfill, not an incremental update.
Breakdown: Form 4 285,306 -- 8-K 57,066 -- NT 10-Q 32 -- NT 10-K 25.

**Flag detector 1: late filing.** `app/services/flag_detector.py` --
trivial existence check (an NT 10-K/10-Q filing IS the flag, no content
parsing needed). Ran to completion: 57 flags, all 57 NT filings processed.

**Flag detector 2: 8-K item codes.** `app/services/flag_detector_8k.py`.
Real bug found and fixed same day (D-008): naive keyword matching against
the full Item 5.02 text (including its standard boilerplate heading, which
always contains "departure"/"appointment" language regardless of actual
content) produced a false positive -- a filing about RTX's CFO joining 3M's
board was flagged as 3M's own CFO resigning. Fixed by stripping the
heading before keyword matching; verified via a 50-filing before/after
test batch (5 flags -> 2 correct flags).

Launched the full 57,066-filing 8-K run in the background at end of
session. **This run later crashed** (see 2026-07-22/23 entry) -- the
version running at session end had no retry/exception handling.

Repo state at end of this session: still zero git commits, living inside
the shared PINNACLE parent repo, nothing version-controlled. Flagged
explicitly as the single biggest risk to the project (a lost Mac = lost
Sentinel entirely).

## 2026-07-22 -- Git repo created, HANDOFF.md written

Initialized a real, standalone git repo (previously nonexistent -- see
2026-07-21 entry). Verified `.gitignore` correctly excluded `.venv/`,
`node_modules/`, `.env`, `*.log`, `__pycache__/` before the first commit
(33 files staged, no bulky/generated content). Created
`github.com/vijs29/pinnacle-sentinel` via `gh repo create`, pushed initial
commit and the crash-prone 8-K detector fix (see next entry) together with
a `HANDOFF.md` documenting full status for a fresh session.

## 2026-07-22/23 -- 8-K job crash found and fixed, then run to completion

Checked on the background 8-K job launched 2026-07-21 -- found it had
crashed with an unhandled `ReadTimeout` from sec.gov at 14,750/57,066
filings, sitting dead since shortly after it started (no automatic
recovery, since neither the fetch function nor the per-filing processing
loop had any exception handling at all).

Fixed:
- `fetch_filing_text()`: retries up to 3x with exponential backoff
  (1s/2s/4s) on network errors, timeout raised 15s->20s.
- `run()` loop: wrapped per-filing processing in try/except so one bad
  filing can never crash the remaining batch -- rolls back just that
  filing's uncommitted state, leaves `processed=False` for retry, continues.
- Added `terminal-notifier`-based progress notifications (title/message/
  sound) every 1,000 filings + a completion notification. Plain `osascript`
  notifications did NOT work reliably on this Mac (Terminal.app doesn't
  self-register with Notification Center for them) -- required
  `brew install terminal-notifier` instead, which registers correctly.

Restarted from the 14,750 checkpoint (only `processed=false` rows queried,
safe to resume, no duplicate work). **Ran to full completion this time:**
all 57,066 8-K filings processed, plus 3 stragglers that failed on the
final batch cleaned up with one more small run.

**Final flag totals, all 5,700+ NT/8-K filings processed:**
- cfo_resignation: 1,972
- late_filing: 57
- auditor_change: 48
- material_weakness: 8
- **Total: 2,085 flags**

(Separately, during this window, a stray copy of the OLD flat pre-redesign
`Filing` schema was found accidentally sitting inside the Pinnacle Quant
repo, untracked -- confirmed as leftover cross-project debris from the
2026-07-21 schema redesign session, not anything Quant-related, and
deleted from the Quant repo before it could be committed there.)

## Current state as of this entry (2026-07-23/24)

- 8-K/NT flag detection: **complete** for all 5 structured flags EXCEPT
  accelerated insider selling.
- Form 4 (insider transaction) data: **285,306 filings already ingested**,
  zero processed -- accelerated insider selling detector not yet built.
  This is the natural next step, and the highest-value flag for the
  short-seller audience (see strategy.md).
- Confluence scorer: not started, straightforward once insider-selling
  exists.
- Outcome validation (`sentinel_outcomes` table): schema exists, nothing
  populates it.
- Frontend: `Landing.jsx`/`Screener.jsx` still don't exist; `/api/filings`
  endpoint still references the old flat schema and will 500 if called.
- Documentation: decisions.md, strategy.md, this journal.md all created
  2026-07-24 to close the "no docs/ files, unlike every other Pinnacle
  project" gap flagged repeatedly in prior HANDOFF.md versions.


## 2026-07-25 -- cfo_resignation false-positive investigation, deferred

Live data check while building the Screener page surfaced a real accuracy
problem: querying /api/filings showed a cfo_resignation flag (SOLV, a
Controller/Chief Accounting Officer appointment) that clearly wasn't a CFO
resignation at all -- the item text mentioned "Chief Financial Officer" only
in passing (identifying who the new appointee reports to), same class of
bug as the RTX/3M false positive found and partially fixed 2026-07-21.

Attempted fix: sentence-level proximity check (require the CFO keyword and
a resignation keyword in the SAME sentence, not just anywhere in the whole
item body) instead of whole-body keyword co-occurrence. Ran a reclassification
test against all 1,972 existing cfo_resignation flags (read-only, never
modified the database): 432 survive, 1,540 would be removed under the
stricter check.

**Verified both directions with real filing text before trusting either
number -- and found the fix itself has a real bug:**
- LVS 2024-01-25 (correctly flagged for removal by the new check): confirmed
  via full text -- this is an employment agreement AMENDMENT for the
  existing CFO (compensation/severance terms), not a resignation. New logic
  correct here.
- AOS 2019-01-14 (INCORRECTLY flagged for removal by the new check):
  confirmed via full text -- this is a genuine, unambiguous CFO resignation
  ("Kita... Chief Financial Officer... advised the Company that he will
  retire..."), CFO title and resignation word in the same real sentence.
  The sentence-splitting regex naively splits on any ". " pattern, which
  incorrectly breaks mid-sentence on the company's own name ("A. O. Smith")
  -- fragmenting a single real sentence into pieces at the abbreviation
  periods, so the CFO title and resignation word end up in different
  fragments and the co-occurrence check fails on genuinely correct data.

**Decision: reverted the sentence-proximity classifier change entirely**
(flag_detector_8k.py restored to its last-committed whole-body-check
version via `git checkout --`). The attempted fix is not reliable as
implemented -- it trades one class of error (false positives from
whole-body co-occurrence) for another (false negatives from naive sentence
splitting on abbreviations), and was not proven net-better before being
caught. No database changes were made either direction -- the
reclassification script was read-only/diagnostic only (removed after use,
app/services/reclassify_cfo_resignation.py). All 1,972 original
cfo_resignation flags remain exactly as originally detected.

**Also flagged, worth remembering:** this entire investigation focused
narrowly on ONE of Sentinel's 5 Tier-1 flag types. auditor_change and
material_weakness have never been spot-checked against real filing text
the way cfo_resignation and the original RTX/3M case were. Precision
across all flag types (not just cfo_resignation) is genuinely unverified
and should be revisited properly -- with a better sentence-boundary
approach (e.g. a real sentence tokenizer, or a fixed-character window
around each keyword instead of naive period-splitting) -- once the core
product (auth, Landing, Screener, insider-selling detector) is further
along. Deliberately deferred, not abandoned.
