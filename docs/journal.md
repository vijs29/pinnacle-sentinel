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


**Wordmark decision confirmed (2026-07-26).** "PINNACLE SENTINEL" wordmark
color: Option E, #d4443f ("signal red"). Cross-checked against
NavBar.jsx (committed this session, commit 5064ec7) -- already
implemented correctly (icon gradient #d4443f -> #b3413e, wordmark text
#d4443f). Styled consistently with Pinnacle Veridia's own product-specific
color-coding convention (veridia.pinnacletranscore.com uses its own
distinct accent color per SKU, per the brand system established in
Pinnacle Quant's April 2026 brand work -- gold shield base, SKU-specific
sub-label colors).


## 2026-07-26 (cont'd) -- XBRL ingestion completed, data quality verified

Full 503-company XBRL companyfacts ingestion completed: 0 failed
lookups, 1,493,566 facts seen (whitelisted concepts), 830,370 new facts
inserted after dedup (gap between seen/inserted is expected -- same
fact commonly reported in both a 10-Q and its comparative 10-K).

**Verification before trusting the data:**
- Per-concept coverage checked: 29 of 30 concepts had real cross-company
  coverage (256-498 companies each, depending on concept -- lower counts
  for e.g. CostOfRevenue/GrossProfit are expected, since not all filers
  report gross margin as a distinct line item).
- Found and fixed a real bug: GoodwillAndIntangibleAssetsNetExcludingGoodwill
  returned ZERO rows across all 503 companies -- wrong/non-standard tag
  name. Corrected to IntangibleAssetsNetExcludingGoodwill (the actual
  standard us-gaap tag) and re-ran ingestion to backfill (PID 29560,
  xbrl_ingest_backfill.log) -- safe re-run, dedup means only the newly
  corrected concept's facts get inserted.
- Spot-checked Apple (CIK 0000320193) NetIncomeLoss against known public
  figures: FY2024 $93.736B, FY2023 $96.995B -- both match Apple's actual
  reported net income. Ingestion values are trustworthy.
- Checked for CIK format inconsistency between filings.cik and
  financial_facts.cik (a real risk, since confluence scoring will need
  to join disclosure flags against quantitative scores by CIK) -- both
  tables store the same 10-digit zero-padded format (e.g. 0000320193).
  No join-breaking mismatch.

**Data is verified and ready.** Next: app/services/quant_scores.py --
Sloan accruals ratio first (simplest, pipeline smoke test), then Beneish
M-Score, then Altman Z-Score (needs market cap, not yet wired in).


## 2026-07-26 (cont'd) -- XBRL backfill bug found, fixed, and verified

Backfill run for the corrected IntangibleAssetsNetExcludingGoodwill
concept initially crashed: UniqueViolation on financial_facts, since
existing_keys (loaded from DB as Python date objects) never matched
freshly-parsed facts (start_date/end_date stayed as raw strings from
SEC's JSON) -- the dedup check silently never matched anything, so the
script tried to re-insert all ~830K already-committed facts and died on
the first collision.

Fixed: parse start_date/end_date with datetime.strptime() before
building the fact dict, so types match what's pulled from the DB.
Also wrapped both the periodic (every-50-company) and final commits in
try/except, matching flag_detector_8k.py's per-batch resilience pattern
-- a future bad chunk rolls back and logs, rather than killing the run.

Re-ran after the fix: 503 companies polled, 2 failed (read timeouts
after 3 retries each -- CIK 0000927653, 0001613103, transient network,
not systematic), 21,361 new facts inserted (all IntangibleAssetsNet-
ExcludingGoodwill, confirmed via COUNT query) -- correctly small this
time, versus the crash-inducing near-830K re-insert attempt before the
fix. Total financial_facts now 851,731. New concept has real coverage:
379 of 503 companies (reasonable -- not every filer separately tags
intangibles apart from goodwill).

xbrl_ingest.py, financial_fact.py, xbrl_concepts.py were also found
sitting uncommitted this session (written via heredoc, never git-added)
-- committed retroactively (f9bbc60) before this backfill re-run.

**XBRL data now fully verified and stable.** Next: app/services/
quant_scores.py, starting with the Sloan accruals ratio.


## 2026-07-26 (cont'd) -- Sloan ratio built, period-matching bug found and fixed

app/services/quant_scores.py + app/models/quant_score.py (quant_scores
table, components stored alongside final value per D-011) built. Sloan
ratio = (NetIncomeLoss - OperatingCashFlow) / Assets, per company per
fiscal year.

**Bug found via spot-check, not assumed correct:** initial run joined
NetIncomeLoss/OCF/Assets by SEC's fy label (fiscal_year field) --
produced implausible outliers (VRT -11.1, CDNS -1.37, both far outside
any real company's possible range). Root cause: SEC's fy/fp fields
describe the FILING's fiscal year, not each fact's actual period -- a
single 10-K reports current + prior-year comparatives, sometimes all
tagged with the same fy label; VRT's 2018 fy bucket mixed a pre-merger
shell-company Assets figure ($25,000, period end 2017-12-31) with a
real post-merger NetIncomeLoss figure from a genuinely different period.

Fixed: join by actual end_date instead of SEC's fy label; duration
facts (NetIncomeLoss, OCF) filtered to 350-380 day spans to exclude
quarterly figures SEC sometimes mislabels fiscal_period='FY' (also
seen in CDNS's raw data); prefer 10-K over 10-Q when both report the
same end_date. Cleared and recomputed: 6,747 ratios (up from the buggy
run's 5,846 -- more companies matched cleanly once join logic was
correct), 486 companies with coverage. Re-checked outlier range after
fix: max +0.61 (GEN), min -1.66 (EXE, 2020) -- EXE's magnitude is
plausible given 2020 oil-price-crash impairments and its later Chapter
11 filing, not re-flagged as a bug.

**Lesson for Beneish/Altman builds next:** do not trust SEC's fy/fp
fields for period-joining across concepts -- always join on end_date
directly, and verify duration spans, the way this fix required.


## 2026-07-26 (cont'd) -- Beneish M-Score built; AQI instability found, flagged not fixed

app/services/quant_scores.py extended with compute_beneish_m_scores() --
8 variables (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA), all
year-over-year, using _prior_year_lookup() (350-380 day window) on top
of the end_date-joined _facts_by_company_period() from the Sloan build.
178 scores computed across 37 companies; 4,304 skipped for missing
current/prior-year data on at least one of the 11 underlying concepts
(expected -- CostOfGoodsAndServicesSold only covers 262/503 companies,
SellingGeneralAndAdministrativeExpense 291/503, and Beneish requires
ALL 8 variables simultaneously, both years).

**Spot-checked outliers before trusting the run (same discipline as
Sloan):** EQT 2024 initially computed AQI=12.56, M-Score=+2.33 --
implausible on its face. Verified by hand against raw financial_facts:
NOT a data bug (facts were clean, single-period, correctly matched).
Real cause: AQI is a ratio-of-ratios that becomes numerically unstable
when a company's "other assets" (1 - (CurrentAssets+PPE)/Assets) is
near zero in either year -- common in asset-heavy industries like oil &
gas E&P. EQT's 2023 balance sheet had CA+PPE = 98.7% of total assets,
leaving almost nothing in the AQI numerator; 2024's Equitrans
acquisition changed that composition, and dividing by a near-zero prior
value blew the ratio up to 12.56 on its own contributing +5.07 to the
M-Score (coefficient 0.404) -- a company would show as severe fraud risk
purely from balance-sheet composition, not from anything a forensic
analyst would actually flag.

**Decision: flag, don't discard or silently trust.** Added
unstable_component boolean to Beneish's stored components -- true if
any of the 7 ratio-of-ratios variables (excludes TATA, which isn't a
ratio-of-ratios) exceeds abs(10). 1 of 178 scores flagged (EQT 2024).
Downstream consumers (confluence scorer, UI) should treat
unstable_component=true scores as needing manual review, not as a
reliable standalone red flag.

Score range otherwise sane: -4.21 (HAS 2023) to -3.70 (BMY 2024) at the
clean end, all well under the -1.78 flag threshold -- consistent with
clean-accounting companies in the S&P 500 universe.

Next: Altman Z-Score -- needs market cap (price x shares outstanding),
not yet wired in per D-010. Will reuse Pinnacle Quant's yfinance
pipeline rather than build a second price feed.
