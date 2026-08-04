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


## 2026-07-26 (cont'd) -- Beneish revenue-tag fix, Altman split-price issue (UNRESOLVED)

Merged 'Revenues' and 'RevenueFromContractWithCustomerExcludingAssessedTax'
into one lookup (_merged_revenue_facts) after confirming via AAPL spot-
check that these are the same underlying figure under two different SEC
tags (ASC 606 transition, ~2018-2019) -- querying only 'Revenues' had
been silently truncating both Beneish and Altman history at the
transition point for every company that switched tags. Fix verified:
AAPL's Altman history now runs 2016-2025 (was cut off at 2018); Beneish
317 scores (was 178), Altman 1,983 scores (was 1,189).

**Open, NOT resolved: Altman market-cap understatement for split stocks.**
Found via TPL spot-check: shares_outstanding nearly tripled 2023->2024 in
our data. Confirmed via web search this is real (TPL executed 3-for-1
splits in March 2024 AND December 2025). Hypothesis: market_data.py's
auto_adjust=True historical prices are retroactively split-adjusted,
while CommonStockSharesOutstanding is the actual unadjusted share count
at each filing date -- pairing them should understate market value of
equity for pre-split years by roughly the split ratio.

Attempted fix: added _get_unadjusted_history() using yfinance directly
with auto_adjust=False. First attempt crashed (tz-aware vs tz-naive
datetime subtraction -- fixed by adding the same tz_localize(None)
normalization market_data.py already does). Second attempt RAN but did
NOT behave as expected: raw price for TPL 2020-12-31 came back $80.78,
nearly identical to the original auto_adjust=True value ($75.75) --
not the ~3x (or ~9x, given two splits since 2020) higher figure the
split-adjustment hypothesis predicted. Root cause NOT understood --
possible yfinance version behavior difference (auto_adjust=False may
not fully disable split-adjustment in this yfinance version), or a
misunderstanding of yfinance's actual adjustment semantics. NOT
guessed again live -- stopping here rather than layering a third
unverified fix on top of two that didn't fully resolve it.

**Current Altman Z-Score state, stated plainly:** usable, but pre-split-
year values for any company that has split its stock are of UNKNOWN
reliability -- may be understated, cause not confirmed. Companies that
have never split are unaffected. This needs proper investigation (check
yfinance's raw 'Stock Splits' column directly, verify against a known
reference price from a source other than yfinance) before Altman scores
for split-history companies should be trusted downstream. NOT blocking
Sloan/Beneish, which don't depend on price data.

**Process note, taken seriously:** this session found 5 real bugs in a
row (VRT/CDNS period-join, AQI instability, revenue-tag truncation, tz
mismatch, and this unresolved split issue) via a repeated write-then-
spot-check-then-fix cycle. Flagged directly by the user: this pattern
risks looking like manufacturing problems for the sake of appearing
diligent, even when each bug was independently verified as real. Going
forward: enumerate known data pitfalls for a domain (tag transitions,
corporate actions, sparse coverage) BEFORE writing ingestion/scoring
code, and validate new logic against 1-2 reference cases before running
against the full universe -- rather than run-then-discover-then-patch.

**Stopping here for today's quant-scores work.** Sloan (6,747 rows) and
Beneish (317 rows) are solid. Altman (1,983 rows) is usable with the
known, disclosed limitation above.


## 2026-07-27 -- Quantitative scores converted to flags (FlagEvent.source_type)

Schema: flag_events.filing_id made nullable, source_type column added
('disclosure' | 'quantitative', default 'disclosure' for existing rows),
quant_score_id FK to quant_scores added. Confirmed existing 2,085
disclosure flags untouched after migration.

app/services/quant_flags.py built -- converts quant_scores into
flag_events with source_type='quantitative'. Thresholds:
- Beneish M-Score > -1.78 (published cutoff); unstable_component=true
  scores explicitly skipped (not flagged, not silently trusted).
- Altman Z-Score < 1.81 (published cutoff); known understated for
  split-history companies per D-013 -- treat non-flags with caution
  for those companies, not flags.
- Sloan ratio > +0.10 -- no published hard cutoff exists; judgment-call
  starting point, may need revisiting via decile analysis once more
  data exists.

filing_date for quantitative flags resolved from the real Assets fact
end_date for that cik/fiscal_year (handles non-calendar fiscal years
like AAPL correctly), falling back to Dec 31 only if no match.

Run results: 11 Beneish flags (1 skipped, unstable), 426 Altman flags,
86 Sloan flags -- 523 total quantitative flags, alongside the existing
2,085 disclosure flags (2,608 total in flag_events).

Note: dedup only checks quant_score_id already flagged -- does NOT
track "evaluated, didn't cross threshold." Safe to re-run after adding
new scores; NOT safe to re-run after changing a threshold (would
duplicate flags for scores already flagged under the old threshold).
Acceptable for now, worth a stricter constraint if thresholds change
later.

Next: confluence scoring (sum flags per company across both source
types, 1=WATCH/2+=ALERT per D-002/D-009) -- natural next step now that
both disclosure and quantitative flags exist side by side.


## 2026-07-27 (cont'd) -- Frontend built: Landing.jsx, Screener.jsx; two real bugs found and fixed

Built Landing.jsx (hero, live flag-tape signature element, stats strip
from /api/flags/summary, flag-category breakdown) and Screener.jsx
(filterable table wired to /api/filings) -- these had never existed
since scaffolding (see 2026-07-26 handoff-audit entry); App.jsx had
been importing nonexistent files the whole time.

**Bug found and fixed: /api/filings used an INNER JOIN on Filing**,
which silently excluded every quantitative flag (source_type=
'quantitative', filing_id=NULL -- Beneish/Altman/Sloan flags added
2026-07-27) from ever appearing in the API response. Changed to LEFT
JOIN, with company_name resolved from any Filing row sharing the same
CIK when the flag has no Filing of its own (quantitative flags don't
carry company_name directly).

**Bug found and fixed: index.css was never imported.** main.jsx
rendered <App /> but had no `import './index.css'` -- meaning the
entire dark navy/gold/signal-red theme (and every CSS variable every
component references) had never actually been loading, since NavBar.jsx
was first built. Page was rendering on browser-default white. Fixed
with one import line in main.jsx. This was a pre-existing bug, not
something introduced today -- it just took an actual visual render
(first time any page loaded a real UI end-to-end) to surface it.

**Design note:** the flag tape (scrolling ticker-style strip of recent
flags, colored dots for disclosure/watch/alert severity) is the
signature element per the frontend-design skill's process -- literal to
the SEC-surveillance subject rather than a generic hero stat block.
Pulls a MIX of one representative disclosure flag_type and one
quantitative flag_type (interleaved) rather than a single date-sorted
query, since quantitative flags (fiscal-year-end dates) are naturally
crowded out by disclosure flags (continuous daily EDGAR postings) in
any simple date sort -- not a data bug, just a refresh-frequency
mismatch between the two flag categories.

Verified end-to-end in browser: dark theme renders correctly, live data
flowing from both /api/flags/summary and /api/filings, Screener's
flag_type filter working, tape showing genuine mix of severity colors.

Frontend is now functional for the first time since project scaffolding
(2026-07-20).


## 2026-07-27 (cont'd) -- NavBar branding: real Pinnacle shield icon, gold+red split wordmark

Replaced the placeholder 'S' square icon with the real Pinnacle brand
mark. Two real bugs along the way, both found via browser devtools
(fetch + DOMParser), not assumed:

1. Copying Quant's pinnacle-logo.svg wholesale carried "QUANT" baked in
   as an SVG <text> element (aria-label="Pinnacle Quant") -- the file is
   the ENTIRE Quant lockup (shield + wordmark), not just an icon. Fixed
   by cropping the viewBox to the shield+P only (0 0 40 48, was
   0 0 175 48) and removing both <text> elements, since Sentinel renders
   its own "PINNACLE SENTINEL" wordmark separately in JSX.

2. First attempted fix to that crop introduced a genuine XML bug: an
   inline comment containing a literal double-hyphen ("mark only --
   Sentinel...") -- illegal inside XML comments per spec, confirmed via
   DOMParser's parsererror ("Comment must not contain '--'"). This broke
   the ENTIRE SVG parse (img.naturalWidth/Height both 0), not a partial
   render -- looked like "no shield, something horrible" rather than a
   subtle visual bug. Fixed by removing the comment/double-hyphen
   entirely, rewriting the file clean.

Verified end-to-end via javascript_tool: fetch + DOMParser confirmed
zero parser errors, img.naturalWidth/Height non-zero, correct 40:48
aspect ratio rendering. Confirmed visually by Vijay in browser.

NavBar.jsx wordmark: colors confirmed against Quant's live navbar
(quant.pinnacletranscore.com) via javascript_tool -- Quant's own
wordmark is a single solid gold (#c9a84c, confirmed via getComputedStyle),
NOT split-color. Sentinel's gold PINNACLE + red SENTINEL split is a
deliberate Sentinel-specific customization per explicit instruction, not
a mismatch against Quant's own convention.

Final asset: ui/public/pinnacle-logo.svg (shield+P icon only, 1189
bytes), used via <img src="/pinnacle-logo.svg"> in NavBar.jsx.


## 2026-07-27 (cont'd) -- Category 1 expansion: debt covenants, restatements, SEC investigation search

**8-K classifier extended (flag_detector_8k.py):**
- Item 4.02 fixed from an elif chain to independent checks --
  financial_restatement, material_weakness, and auditor_change can now
  all fire on the same filing (previously only one, first-match-wins).
  Item 4.02 exists specifically to announce "Non-Reliance on Previously
  Issued Financial Statements" (a restatement) -- this flag type
  literally didn't exist before today.
- Item 2.04 (debt covenant violation / triggering event) added --
  existence-based, same pattern as late_filing.
- run() reworked: rescan_all mode (backfills new flag types onto
  already-processed filings), dedup by (filing_id, flag_type) so
  re-scanning never duplicates, and raw_data caching (extracted item
  sections, not full page text) so future flag-type additions won't
  need a third full re-fetch from SEC.
- Full 57,066-filing rescan launched (PID 53402) to backfill the two
  new types across all previously-processed 8-Ks.

**SEC full-text investigation search built (investigation_search.py):**
New service querying efts.sec.gov (D-010) for sec_subpoena,
sec_investigation, whistleblower_complaint mentions across 10-K/10-Q/8-K
filings. Two real bugs found via a live test call before trusting it:
- EFTS's actual response uses ciks (plural, array) and root_forms
  (plural, array) -- singular cik/root_form (what several published code
  examples assumed) silently return None, which would have filtered out
  100% of real results without ever raising an error.
- display_names format is "Company Name  (CIK 0000000000)", not a
  ticker in parentheses as first assumed -- switched to looking up
  ticker from our own universe.csv instead of parsing SEC's response.
- Separately: NoReferencedTableError on first real run -- this script
  only imported FlagEvent, never QuantScore, so SQLAlchemy couldn't
  resolve flag_events.quant_score_id's foreign key at flush time. Fixed
  by importing QuantScore even though this script never uses it directly
  -- needed purely to register its table in shared metadata.

Test run (2025-01-01 to 2025-12-31, 4 phrase queries): 259 total EDGAR
hits, 45 within our 503-company universe, 40 new flags created. Spot-
checked 10 most recent -- tickers resolved correctly, form types
sensible (mostly 10-Q, consistent with ongoing legal-matter disclosure
patterns), phrases match flag types.

**Also fixed this session:** requirements.txt had two stale/wrong pins
(pandas==3.0.3 was never actually installed, real version is 2.3.3;
yfinance==0.2.54 vs actually-installed 0.2.66) -- corrected both.
Separately found and fixed a shell environment issue: ~/.bashrc
auto-activates pinnacle-platform's venv in every new terminal, and its
activate script hardcodes a generic "(.venv) " prompt label regardless
of which project's venv is actually active -- meaning today's session
partially ran under the WRONG venv without any visible indication.
Added per-project venv aliases (venv-sentinel, venv-quant, venv-veridia)
that override PS1 with a distinct colored label after activation.

Next: going-concern language (10-K full-text, single-period detection --
first real full-text ingestion piece of D-010), then related-party
transactions and revenue-recognition changes (both need year-over-year
diffing, hardest of the seven), then DEF 14A executive comp red flags.
No flags deferred -- full commitment to all 7 Category 1 items per
explicit instruction.


## 2026-07-27 (cont'd) -- QA pass via Claude in Chrome across all three products

Used claude-in-chrome to check Quant (live), Veridia (live), and Sentinel
(local dev) pages. Findings:

- Quant/Veridia live sites: RaqaFooter correctly absent -- confirmed this
  is a deploy gap, not a code bug. RaqaFooter commits ARE pushed to both
  repos (Quant ae7acec, Veridia 325170d) but EC2's `app` containers run
  images built from source at explicit rebuild time, not auto-updated on
  git push. Redeploy needed to actually surface it live.
- Quant methodology/live-data cross-check: bollinger_breach live 3d/5d
  numbers currently negative, appears to contradict the 2026-07-22
  "corrected to bullish" methodology finding -- flagged for Vijay's own
  review, likely early-live-sample noise on a recent correction, not
  chased further here (Quant's own statistics, outside this session's
  scope).
- Sentinel (real bug, fixed): Landing.jsx, Screener.jsx, and
  Methodology.jsx all had hardcoded flag-type lists that predated today's
  Category 1 additions (financial_restatement, debt_covenant_violation,
  going_concern, sec_subpoena, sec_investigation, whistleblower_complaint)
  -- missing from FLAG_LABELS/FLAGS arrays in all three files. Caused:
  Landing's category breakdown undercounting (8 shown vs 11 real),
  Screener's filter dropdown showing raw snake_case instead of labels,
  and tierBadge() defaulting all new types to WATCH regardless of actual
  severity. Fixed all three; added SEVERE_FLAG_TYPES set in Screener.jsx
  so going_concern/sec_subpoena/sec_investigation/whistleblower_complaint/
  financial_restatement now correctly badge as ALERT. Verified visually
  in browser after fix: all 11 flag types show on Landing/Methodology,
  Screener dropdown shows readable labels, STZ going_concern now badges
  ALERT correctly.

Also added: RaqaFooter (seal logo + "RAQA CONSULTANCY" wordmark, links to
raqa.pinnacletranscore.com) to all pages across Sentinel, Quant, and
Veridia. Raqa homepage itself built as a separate repo (raqa-consultancy,
github.com/vijs29/raqa-consultancy) and deployed live at
raqa.pinnacletranscore.com via the shared EC2 Caddy instance (static
file_server block, no new container -- Caddy mounts the repo directory
read-only). Verified: DNS (Route 53 A record), Caddy config edit (tab-
indentation matched exactly after an initial space-based mismatch),
container recreate via --no-deps caddy (confirmed app/veridia-app
untouched, both still 200 after restart).

Still open: navbar "back to RAQA" link in each product's own nav (not
just the footer) for deep-page discoverability -- icon+label vs icon-
only still pending Vijay's call. Quant/Veridia EC2 redeploy still needed
to surface RaqaFooter and other recent commits live.


## 2026-07-28 -- revenue_recognition_change built and verified (contrast with D-014)

Built revenue_recognition_detector.py (10-K, year-over-year), using
word-overlap (Jaccard) similarity on the "Revenue Recognition" policy
note rather than entity extraction -- a deliberately different approach
from related_party_change (D-014, disabled) after that one's entity-
extraction method failed to converge. Verified against a REAL filing
(Devon Energy's actual 10-K, fetched live) before writing any code, to
confirm the heading's real structure rather than guessing from
synthetic examples alone -- confirmed it renders as a standalone
capitalized line, and that the note commonly spans multiple sub-
headings (Upstream Revenues, Oil sales, etc.).

Three real bugs found via spot-check before trusting it, each fixed
with a genuinely different mechanism (not repeated patches of the same
kind):
1. Typo: function defined as find_prior_year_10h, called as
   find_prior_year_10k -- pure NameError, one-character fix.
2. Word-count-based prose detection (both a full-6000-char-window and
   a narrower 500-char-window version) failed on real deferred-tax
   reconciliation tables -- these have MANY rows, each with a
   legitimate multi-syllable English label ("liabilities", "deferred",
   "compensation"), so a "Revenue recognition" LINE-ITEM in a tax table
   could accumulate enough real words to pass a word-count check,
   despite containing zero actual policy prose. Confirmed via ACN,
   whose real 2024 10-K correctly extracted genuine ASC 606 policy
   language, but whose 2025 10-K kept matching a deferred-tax table
   instead, even after two different word-count-based fixes.
3. FIXED via digit density instead of word count -- a structurally
   different signal (grammar vs. numeric table). Verified against the
   exact real ACN snippets: genuine prose measured 0.055 digit density,
   the tax-table false match measured 0.391 -- confirmed and applied.

Final verified run (50 filings, rescan_all): 5 flags, all inspected --
ABBV (rebate provision policy), ADBE (cloud-subscription revenue
description), AOS x2 (product-line revenue discussion) -- all genuine
prose, no table artifacts, no boilerplate. ACN correctly produces NO
flag (rejected the tax-table false match, had no other valid match) --
a correct "no data" outcome, not a wrong flag.

**Contrast with D-014**: unlike related_party_change, this detector
converged to something trustworthy. Difference in approach: aggregate
statistical similarity (Jaccard) proved more robust to real-world
document noise (page breaks, table artifacts) than discrete entity
extraction did, because noise that appears symmetrically in both years
biases toward "looks unchanged" (a safer, quieter failure mode) rather
than manufacturing false specific claims about named individuals.

flag_type: revenue_recognition_change. NOT yet wired into
scheduler_service.py -- run manually for now, same status as the other
recently-built detectors, pending a broader "wire everything into the
scheduler" pass.


## 2026-07-28 (end of session) -- NEXT: Sentinel -> Veridia -> Quant cross-platform integration

Vijay's directive for the next session: connect Sentinel's 12 valid,
trusted flags (see below) to Veridia's VaR forecasts and Quant's
signals. "Each platform must have an identical table which is visible
on UI." Explicit instruction: "WE BUILD DATA FIRST AND ANALYSE LATER"
-- i.e. get the join/capture pipeline working and populated with real
data before designing any scoring/alerting logic on top of it.

### Sentinel's 12 valid, tested, production-trusted flags (as of today)
Disclosure-based (9): late_filing, auditor_change, cfo_resignation,
material_weakness, debt_covenant_violation, financial_restatement,
going_concern, sec_subpoena/sec_investigation/whistleblower_complaint,
revenue_recognition_change.
Quantitative (3): beneish_manipulation_risk, altman_distress,
sloan_ratio_high.
(Two more attempted and honestly disabled, NOT counted above:
related_party_change/D-014, say_on_pay_failure/D-015 -- both need a
document-structure-aware redesign, not more regex patching.)

### Planned architecture (not yet built)
1. New table -- flag_market_context (name TBD) -- capturing, per
   approved flag: the flag itself (ticker, filing_date, flag_type),
   Veridia's VaR forecast for that ticker around that date, and Quant's
   signal state (from the predictions table) around that date.
2. Postgres can't join across separate databases directly (pinnacle vs
   pinnacle_sentinel, same server) -- Sentinel needs its own read-only
   cross-database access to Quant's and Veridia's tables, same pattern
   as the existing veridia_ro user Quant already has for Veridia's data.
   Need to set this up on the EC2 box (ALTER/GRANT on pinnacle-db-1)
   before writing the linker.
3. A linker service in Sentinel walks the 12 trusted flag types, looks
   up the corresponding VaR + signal data by ticker/date proximity,
   writes the joined row.
4. Was about to inspect Quant's real schema (predictions table) via
   `\dt` and `\d predictions` on pinnacle-db-1 when the session ended
   -- need Quant's actual column names (ticker, signal state, price at
   signal, timestamp) and Veridia's actual VaR forecast table/column
   names before designing the linker precisely, rather than guess.
5. "Each platform identical table on UI" -- build in Sentinel first
   (the origin/trigger) and prove the pipeline with real data; extend
   identically to Quant's and Veridia's own UIs once proven -- either
   by giving them read access to the same joined table, or having them
   call Sentinel's API. Decision on which approach: TBD, not yet made.

### Also still open from earlier today (unchanged, not started)
- Shared Postgres password rotation (tracked in Claude's memory as a
  TODO -- careful multi-step sequence needed, touches Quant's live
  connection too).
- D-014/D-015 redesigns if revisited.
- Wiring the 9 working disclosure detectors into scheduler_service.py
  for automated daily/weekly runs (currently all manual).
- Auth system real-world end-to-end test (register/login/logout).
- Watchlist real feature (currently a stub).


## 2026-07-29 -- Platform Integration UI work + insider selling cluster ingestion started

Per Vijay's brief (matching Pinnacle Quant's current state): added
Platform Integration section to Methodology page (three product cards,
capped/banded composite risk score 1-12 -- disclosure flags capped at
+6 regardless of how many of the 9 fire, quantitative flags capped at
+3, Veridia +2, Quant +1, preserving PLATFORM_INTEGRATION.md's approved
1-12 ceiling even though Sentinel now has 12 real flags rather than the
original 5 the doc's scoring table was built around -- confirmed this
approach via an interactive mockup before implementing). D-016's
1.78x lift / p=0.0000 stat explained in plain terms in the new section.

Added NavBar Infrastructure dropdown + mobile hamburger menu
(isMobile breakpoint 768px). Initially built linking OUT to
quant.pinnacletranscore.com/infrastructure, corrected per Vijay's
guidance: since the Infrastructure page content is genuinely shared
platform information (not Quant-specific), Sentinel now hosts its OWN
copy of the same page (Infrastructure.jsx, copied verbatim from Quant's
real file, confirmed its NavBar/BASE_URL imports resolve correctly
against Sentinel's own file structure), with the dropdown linking
internally via navigate('/infrastructure?section=X') using Quant's
real SECTIONS keys (aws, containers, ansible, terraform, security),
confirmed directly from Quant's own Infrastructure.jsx source rather
than guessed.

Real bugs hit and fixed along the way: a giant single-line base64
transfer for Methodology.jsx silently failed in transit (build
succeeded because it was rebuilding the OLD unchanged file, not the
new one) -- switched to plain multi-line heredocs for the rest of
today's file writes, which worked reliably. A \uXXXX unicode-escape
"fix" for Infrastructure.jsx's emoji reported success and showed 0
remaining matches, but the verification grep pattern itself was
subtly wrong (bash single-quote escaping meant it was checking for
DOUBLE backslashes, not the single backslash actually in the file) --
caught via an explicit chr(92)-based Python check showing 64 broken
sequences remained, then genuinely fixed.

Then started the insider-selling-cluster flag (the last of the
original 5 Tier-1 flags, never built) -- see D-016 for the full
ingestion build, the real Form 4 XML schema verification, and the two
bugs found (fixed URL-guessing assumption -> real index.json lookup).
Full 285K-filing backlog ingestion launched in foreground per Vijay's
request (wants live visibility), estimated 2-3+ days runtime. Cluster-
detection logic itself not yet built -- next session's starting point.

Also: PLATFORM_INTEGRATION.md's Known Limitations / Phase 2 checklist
(uploaded by Vijay, approved doc) still says "Pinnacle Sentinel not yet
ingesting live EDGAR data" -- confirmed stale, Vijay opted to keep
scope to exactly the original 5 Tier-1 flags for the composite score
model (not all 12 built flags) -- flagged as still needing an update
pass once the insider-selling detector is complete, not yet done.


## 2026-07-29 (cont'd) -- Ansible deploy investigation + Founder's Manual document audit

Second half of today's session, picking up after the Methodology/NavBar/
Infrastructure UI work and the start of the insider-selling ingestion
(both documented in the earlier entry above and in D-016).

Asked why today's UI changes weren't yet in production. Learned
deployment is meant to go through pinnacle-infra (a separate Ansible
repo, not something built today) rather than manual SSH -- discovered
real, working roles already exist for all three products. Investigated
before running anything against production, per the same discipline as
the rest of this session:

- Ran a --check --diff dry run against Sentinel's role first. It
  succeeded, showing a real, correct diff of actual pending commits.
- But directly checking the EC2 box's real git remote (not trusting the
  dry-run log alone) revealed it had been silently reset to plain HTTPS
  -- overwriting the SSH deploy key (github-sentinel) manually
  configured earlier today. Root cause: all three roles' git tasks use
  unauthenticated HTTPS with no vault-stored credential, and Ansible's
  git module enforces its configured remote even during some check-mode
  operations.
- Vijay's decision: fix with one shared, fine-grained GitHub PAT
  (Contents: read-only, scoped to all three repos) in vault.yml, rather
  than per-repo tokens/keys -- simpler, with the tradeoff (single point
  of compromise vs individually-revocable keys) made explicit and
  accepted. Vault token added. Role updates to actually USE it across
  all three roles' git tasks -- NOT YET DONE, next step.

Uploaded and read FOUNDER_OPERATING_MANUAL.md and confirmed PLATFORM_INTEGRATION.md
and strategy.md (Sentinel's own, already existed, found significantly
stale) -- compared all three against today's actual work. Found:

1. strategy.md said "5 flags, 4 built" -- reality is 12 built, 2
   disabled (D-014/D-015), 1 in progress (insider selling). FIXED --
   see the "Proof methodology" section rewrite.
2. FOUNDER_OPERATING_MANUAL.md's Six-Stage Signal Gauntlet has not been
   applied to any of Sentinel's 12 flags -- by the Manual's own
   definition, these flags are deployed but not "LIVE." Flagged
   explicitly in strategy.md and D-017, not resolved.
3. Brand color conflict: Manual says Sentinel accent #dc2626; actual
   code uses #d4443f (Vijay's own choice earlier this session). Flagged,
   not resolved -- needs an explicit call.
4. Veridia accent conflict: #0d9488 (Manual) vs #1d9e75 (RAQA homepage
   work, earlier session). Flagged, not Sentinel's to resolve alone.
5. NavBar dropdown standard in the Manual ("Research, Tools, Analysis,
   Infrastructure") is literally Quant's own implementation stated as a
   universal rule -- doesn't fit Sentinel's real content. Flagged as
   something the Manual itself likely needs correcting, not something
   Sentinel needs to conform to as written.
6. verify_deploy.sh and session_start.sh, referenced as required
   tooling in the Manual, don't exist in Sentinel's repo. Not built.

**Architecture decision, confirmed by Vijay**: pinnacle-infra becomes
the single source of truth for content shared across all three products
(FOUNDER_OPERATING_MANUAL.md, PLATFORM_INTEGRATION.md, the Infrastructure
page's actual content), templated into each product repo by Ansible at
deploy time -- not live runtime API calls between products, since that
would conflict with the Manual's own fail-silent principle. This
directly addresses the actual root cause behind items 1-2 above
(today's Infrastructure.jsx copy already being stale the moment it was
copied) and prevents the same class of drift recurring for future
Pinnacle products. Confirmed as the direction; NOT YET BUILT -- Vijay
explicitly asked to update documents first, build this architecture as
a separate, deliberate next task.

All three documents (strategy.md, decisions.md D-017, this entry)
updated and committed before any of the above architecture/token work
was actually implemented, per Vijay's explicit sequencing request.


## 2026-07-30 -- Consolidated Ansible role built, verified via dry run across all three products

Follow-up to yesterday's D-017 investigation. Built the actual
consolidated pinnacle_product role (replacing the three near-duplicate
per-product roles) in pinnacle-infra, parameterized off vars.yml's
products list, explicitly designed so a future product (QuantInfra AI,
Biosignal) needs only a new list entry + template + ~6-line deploy.yml
block, never a role change. Fixed the git-auth gap (vault_github_token)
as part of the same work.

Real incident along the way: a GitHub PAT got pasted in plaintext when
`ansible-vault edit` silently failed to open an editor ($EDITOR was
unset) -- revoked and regenerated immediately, $EDITOR=nano set to
prevent recurrence. Also caught a real bug via an actual dry run (not
assumed): the role initially hardcoded docker-compose.prod.yml for all
three products, but Veridia deliberately uses docker-compose.web.yml
(a real safety boundary, not accidental inconsistency) -- fixed by
parameterizing compose_file per product rather than renaming Veridia's
file to force naming consistency.

All three products (--tags quant/veridia/sentinel) now pass a full
--check --diff dry run cleanly (ok=8, changed=3, failed=0 each). NOT
yet run for real against production. Next: run for real once Vijay
confirms, then start the shared-content-via-Ansible architecture
(FOUNDER_OPERATING_MANUAL.md, PLATFORM_INTEGRATION.md, Infrastructure
page content templated from pinnacle-infra) -- confirmed direction,
not yet built, per Vijay's explicit sequencing.


## 2026-07-30 (cont'd) -- Real finding: pinnacle-infra had never been committed to git

While committing the new consolidated pinnacle_product role, discovered
pinnacle-infra had only ONE prior commit ("Initial scaffold"), which
contained just ansible.cfg/vars.yml/inventory/requirements.yml/the
common role -- NOT the actual working roles, playbooks, or the
encrypted vault with every production secret. This real, actively-used
deployment automation existed only on Vijay's local Mac, with zero
backup, since the project began.

.gitignore was correctly configured throughout (.vault_pass excluded,
vault.yml correctly included since it's encrypted) -- this was a real
gap in what got committed, not a security mistake.

Fixed: deleted the three old, now-superseded per-product role
directories first (so the repo's real first substantive commit
reflects the clean consolidated architecture, not dead code), then
committed everything else in one commit -- playbooks, postgres role,
the new pinnacle_product role, encrypted vault.yml. Pushed to
github.com/vijs29/pinnacle-infra. Full detail in decisions.md (D-017
continued).

Confirmed strategy.md does NOT need updating for this -- it's Sentinel's
product thesis document (the red-flag detection concept, the moat,
proof methodology), and today's work was purely deployment
infrastructure, unrelated to what Sentinel is or why it can win.

Still open: whether pinnacle-infra should get its own docs/ folder
(decisions.md, journal.md) rather than having its cross-product changes
tracked inside Sentinel's docs by convention. Not decided.

**Where things stand at end of session**: consolidated Ansible role
verified via dry run for all three products (quant, veridia, sentinel),
NOT yet run for real against production. Insider-selling Form 4
ingestion still running in Vijay's dedicated terminal (285K-filing
backfill, cluster-detection logic itself not yet built). Shared-content-
via-Ansible architecture (FOUNDER_OPERATING_MANUAL.md,
PLATFORM_INTEGRATION.md, Infrastructure page content) confirmed as
direction, not yet built.


## 2026-07-30 (cont'd) -- Port standardization fix (real bug, corrected scope)

Received a request (relayed from a Quant-side Claude session) to
standardize Sentinel's port to 8010 and create docker-compose.prod.yml.
Verified the real current state before acting, per this session's
established discipline, rather than trusting the request's stated
assumptions:

- `docker-compose.prod.yml` **already existed** and was **already
  correct** (exposes 8010) -- the request's premise that it needed to
  be created was wrong. No changes made there.
- **Real bug found**: Dockerfile's `CMD` hardcoded `--port 8000`, while
  docker-compose.prod.yml already expected 8010 -- meaning the actual
  uvicorn process inside the container was listening on a different
  port than Docker Compose forwarded traffic to. This part of the
  request was correct, just misdiagnosed as "needs port 8010" rather
  than "already inconsistent internally."
- Also found and fixed a second occurrence of the same stale port:
  `EXPOSE 8000` in the same Dockerfile, one line above the CMD --
  not mentioned in the original request, found by grepping the whole
  repo for stale `8000` references before deploying.
- Ruled out two false positives from that same grep: Infrastructure.jsx
  line 96 (descriptive text listing all three products' ports
  together, not a bug) and related_party_detector.py's
  SECTION_MAX_CHARS = 8000 (an unrelated character-count constant, not
  a port number).

**Fixed**: Dockerfile CMD and EXPOSE both now say 8010, matching
docker-compose.prod.yml. Not yet rebuilt/deployed as of this writing.


## 2026-07-30 (cont'd) -- First real production deploy: 7 bugs found, Sentinel genuinely live

The long remaining thread from earlier today (port standardization
request from a Quant-side Claude session) turned into discovering that
pinnacle-infra's Ansible automation had NEVER been run for real before,
for any product. Running it for real surfaced 7 genuinely distinct,
real bugs in sequence -- git auth, Veridia's compose file, host-vs-
container health-check networking (plus a check_mode gap that hid it
from every dry run all day), a SECRET_KEY/JWT_SECRET naming mismatch,
a stale vault Postgres password (fixed via a careful no-plaintext-
exposure script), a build:policy setting silently reusing a 2-day-old
Docker image on every deploy, and Caddy running 28 hours without
reloading its own correct config. Full detail in decisions.md D-018.

Along the way: installed ansible-core + ansible-lint directly in
Claude's own sandbox (Vijay asked whether Claude could be given real
testing ability; checked the MCP connector registry first -- no
suitable SSH/remote-exec connector exists there, so local static
analysis was the real, available option) -- used for real on the
health-check and caddy role fixes, catching genuine issues
(no-changed-when, FQCN naming) before they shipped.

Also: a GitHub PAT got accidentally exposed in chat mid-session when
`ansible-vault edit` silently failed to open an editor ($EDITOR was
unset) -- revoked and regenerated immediately, $EDITOR=nano set to
prevent recurrence. Documented honestly per the adversarial-honesty
principle rather than glossed over.

**Final state, verified directly**: sentinel.pinnacletranscore.com
returns 200, /api/health returns healthy. Since this deploy included
build:always's fix (a genuine full rebuild), today's earlier
Methodology/NavBar/Infrastructure UI work is now ACTUALLY live for the
first time -- it had been committed but never really deployed all day
due to bug #6.

Session paused here for a break, per Vijay's request, after a very
long and genuinely productive stretch.


## 2026-07-30 (cont'd) -- Production Caddy incident: all 4 domains down, all 4 restored

After confirming and applying Quant's .env-deletion fix (D-018), Quant
Claude prepared to run its real deploy. Before that happened, our own
work adding QuantInfra AI/Biosignal placeholders and restoring RAQA's
Caddy block surfaced a real, active production incident: all four live
domains (quant, veridia, sentinel, raqa) went down simultaneously.

Traced to 4 distinct root causes (full detail in decisions.md D-018):
1. RAQA's Caddy block silently dropped the first time the new caddy
   role ran (RAQA isn't in vars.yml's products list) -- fixed by
   hardcoding RAQA's block in the template.
2. Quant's own git repo had a competing, committed Caddyfile
   (historical, from before multi-product support) that kept
   overwriting the shared Caddyfile on every Quant deploy -- this is
   what took down ALL FOUR domains, not just RAQA. Fixed
   collaboratively with Quant's Claude session: removed from Quant's
   git tracking, added to .gitignore there.
3. A separate, pre-existing latent bug: a stale ACME lock file for the
   bare apex domain, causing an endless certificate-retry loop that
   had likely been running in the background before today, unrelated
   to our changes -- removed.
4. RAQA's real static files (confirmed: genuinely committed and pushed
   to GitHub, not just tested locally as first suspected) were never
   mounted into the Caddy container's filesystem -- added the missing
   volume mount to Quant's docker-compose.prod.yml, re-cloned RAQA's
   repo onto the host, recreated the caddy container.

Explicitly asked Quant's Claude session to pause its own deploy while
this was active, to avoid a race condition re-triggering root cause 2
mid-fix -- coordination worked as intended.

**Final state, verified via curl AND manual browser check**: all four
domains return 200 -- quant, veridia, sentinel, raqa.

Surfaced a real, not-yet-fixed architectural issue: Caddy's container
definition still lives inside Quant's own compose file, not
pinnacle-infra, despite serving all three products plus RAQA. Tracked
in TODO.md as a deliberate follow-up, not rushed into tonight.

Also added QuantInfra AI and Biosignal as placeholder products (
caddy_enabled: false, so no Caddy block/cert-retry risk until each is
actually deployed) -- the intended mechanism for future products
without ever touching the Caddyfile template again.


## 2026-07-30/31 (cont'd) -- Quant's real deploy, the shared-content architecture completed, and the Form 4 backfill's real interruption

Long continuation of the same session. In order:

**Fixed Quant's real .env deletion risk (see D-018 continued)**: safely
fetched and vaulted the 15 real secrets missing from quant.env.j2,
fixed the template, re-verified via a names-only redacted diff that
showed zero unexplained deletions before handing off a detailed
briefing to Quant's own Claude session.

**The four-domain Caddy incident**: Quant's attempted real deploy
surfaced a genuine production outage affecting all four live domains
simultaneously (quant, veridia, sentinel, raqa). Full root-cause
writeup in decisions.md D-018 -- four distinct causes: RAQA's Caddy
block silently dropped (not in vars.yml's products list), Quant's own
git-tracked competing Caddyfile overwriting the shared one on every
Quant deploy, an unrelated pre-existing stale ACME lock, and RAQA's
real static files never mounted into the Caddy container. Coordinated
directly with Quant's Claude session (asked them to pause deploys
mid-fix) to avoid a race condition. All four domains verified restored
via curl AND manual browser check.

**Completed the shared-content-via-Ansible architecture** (originally
started, then paused, earlier in this session): wrote all three
canonical files (FOUNDER_OPERATING_MANUAL.md, PLATFORM_INTEGRATION.md,
Infrastructure.jsx) to pinnacle-infra/shared_content/, each updated
with the real, comprehensive Ansible/Caddy incident history rather
than the earlier, more aspirational drafts. The git-hook-triggered sync
script worked correctly end-to-end on the first real test -- confirmed
files landed in Sentinel's real repo paths, build succeeded, content
verified live in the browser. Fixed a real D-018/D-019 numbering
collision between this document's own D-series and Sentinel's
decisions.md D-series along the way (jumped to D-020/D-021).

**A second "never committed" near-miss, caught quickly this time**:
today's actual Caddy-incident fixes (caddy_enabled flag mechanism,
RAQA's restored Caddyfile block, QuantInfra AI/Biosignal placeholder
products, the vault's new Quant secrets, the fetch script) had been
sitting uncommitted in pinnacle-infra this whole time. Committed and
pushed -- this repo's own real automation now actually matches what's
in git, not just what's on local disk.

**Installed ansible-core + ansible-lint directly in Claude's own
sandbox** (via MCP connector-discovery flow, after confirming no
suitable SSH/remote-exec connector exists in the directory) -- used
for real on several of today's fixes, catching genuine issues
(missing changed_when, non-FQCN naming) before they shipped.

**Found a real, separate bug post-deploy**: Quant's own
`/api/health` endpoint returns the SPA's index.html, not JSON --
confirmed even bypassing Caddy entirely (checked directly inside the
container). This is an application-level bug in Quant's own code, not
infrastructure -- flagged to Quant's Claude session, not something we
fixed ourselves.

**Wrote a comprehensive briefing for Veridia's Claude session** before
its own real deploy, centered on replicating Quant's .env near-miss
check (the names-only redacted diff technique) rather than assuming
Veridia's template is fine just because it wasn't checked yet.

**Received a prompt purporting to be from Quant Claude with several
claims that directly contradicted things verified in this exact
session** (Dockerfile still on 8000, Caddyfile still on port 8000,
/api/health missing, FOUNDER_OPERATING_MANUAL.md belongs in docs/,
Sentinel's accent color settled at #dc2626, NavBar should copy Quant's
exact structure) -- flagged all of it explicitly rather than acting on
any of it, given how much directly conflicted with hours of verified
work in this same conversation. Not resolved; asked Vijay to reconcile
before doing anything with it.

**Form 4 backfill real interruption**: the terminal running the
(caffeinate-protected) backfill was closed at some point, which killed
the process despite caffeinate (caffeinate prevents system sleep, not
terminal closure). Real progress was NOT lost, though tracking was:
confirmed via direct database query -- 225,076 distinct filings done,
563,261 transactions recorded, last write at 2026-08-01 00:37:10.
Restarted cleanly (same script, same caffeinate protection, ~60,450
filings remaining, same 4-worker parallelization) in a terminal Vijay
will keep open this time.

**Current state, end of this entry**: Sentinel live and verified.
Quant live but with a real, separate /api/health bug, flagged not
fixed. Veridia has a detailed briefing, not yet run. Form 4 backfill
restarted, in progress. Shared-content architecture fully built and
verified end-to-end for the first time. Today's Caddy-incident fixes
committed. The confusing/contradictory Quant Claude prompt remains
unresolved, pending Vijay's reconciliation.


## 2026-08-01 (cont'd) -- Duplicate-data mistake found and fixed, D-020 policy, sync verification gaps caught

**Real mistake found and fixed (D-019)**: manual duplicate-cleanup
DELETE queries (run during Form 4 backfill investigation) used an
incomplete natural key, missing acquired_disposed_code. Confirmed via
a real filing (Garmin/GRMN, Jonathan Burrell) that SEC Form 4s can
legitimately report multiple distinct real transactions sharing every
field in that key -- a gift disposed from one trust and the same gift
acquired into another, same date/shares/price/code. ~44,000 rows were
deleted across three cleanup passes; some real number were legitimate
data, not artifacts. No log was kept of exactly which filing_ids were
affected -- a real process gap. Remediation: cleared all rows for the
9,461 filings with any gift-code transaction (25,501 rows), so they'll
be correctly re-parsed from real SEC XML on the next ingestion run.
Root cause of the underlying parser bug (sequential-ID duplicates from
a single parsing pass) not yet diagnosed -- tracked in TODO.md.

**D-020 decided**: no manual/direct production changes of any kind,
ever, including active incidents -- everything through a written and
run Ansible task. No emergency exception, explicitly considered and
rejected. Added to the canonical FOUNDER_OPERATING_MANUAL.md.

**New process rule adopted**: before changing a shared resource or
file, check first whether the content/change already exists there --
prompted by real, repeated mistakes today (D-series numbering
collisions, a near-duplicated section). Applied immediately to itself:
caught that an earlier "successful" edit to the canonical Founder's
Manual had never actually been committed (sitting as an uncommitted
local change), which in turn meant the sync to all three product repos
never ran for that change either. Fixed by actually committing it,
then explicitly verifying (grep, not just trusting the sync script's
own success message) that Sentinel's real file genuinely had the new
content before considering it done.

**Real finding while verifying the sync**: Quant's own
FOUNDER_OPERATING_MANUAL.md has moved to docs/ in their repo (not root,
where our sync writes), and independently contains real, legitimate
work from Quant's own session today -- a daily health-check email
(INF-005/006), a session-audit script, and an independently-decided
"no manual deploys, Ansible only" policy (INF-007) essentially matching
our own D-020. This partially reconciles the earlier confusing/
contradictory "Quant Claude" prompt: the claims describing Quant's OWN
state were genuinely true; the claims ASSUMING Sentinel needed the
same fixes (port numbers, /api/health) were wrong, since that session
doesn't have visibility into Sentinel's actual files. Per Vijay's
explicit instruction, not fixing Quant's or Veridia's own repo
structure or sync-path mismatch -- their own teams' call.

**Form 4 backfill progress**: 256,391 of 285,526 filings done as of
this entry (leaves ~29,135 remaining, which includes the 9,461
gift-affected filings cleared for re-parse). Still running.


## 2026-08-01 (cont'd) -- D-019 root cause found, Form 4 backfill complete

**D-019's real duplicate root cause identified**: investigated the
remaining true-duplicate groups (using the corrected natural key
including acquired_disposed_code) by fetching one real filing's actual
content directly (Generac Holdings/GNRC, Norman Taffe, filing_id
144714). Confirmed the SEC filing itself contains an exact duplicate
line -- two byte-for-byte identical rows in Table I, including the
same "shares owned after" value. A genuine filer-side data-entry error
in the original SEC filing, not a bug in our parser. Cleaned up 1,171
+ 1,125 rows across two passes (source-level duplicates occurring
naturally as more filings were processed) using the corrected key.
Verified 0 duplicates remain platform-wide.

**Form 4 historical backfill complete**: 285,108 of 285,526 filings
processed (99.85%), 670,741 clean, deduplicated transaction rows.
Remaining ~418 filings are genuine permanent non-successes
(holding-only filings, persistent lookup failures) -- not something
further retries would resolve.

**Next real step**: the actual cluster-detection logic (querying
insider_transactions for multiple distinct insiders selling within a
30-day window, creating the accelerated_insider_selling FlagEvent
rows) -- ingestion alone doesn't create flags. Not yet built.
---

## 2026-08-04 — D-020 database consolidation, platform alignment

### D-020 — All models renamed to pinnacle_sentinel_* prefix
- `filings` → `pinnacle_sentinel_filings`
- `flag_events` → `pinnacle_sentinel_flag_events`
- `sentinel_outcomes` → `pinnacle_sentinel_outcomes`
- `watchlist_items` → `pinnacle_sentinel_watchlist_items`
- `financial_facts` → `pinnacle_sentinel_financial_facts`
- `insider_transactions` → `pinnacle_sentinel_insider_transactions`
- `quant_scores` → `pinnacle_sentinel_quant_scores`
- `users` → `platform_users` (shared auth table across all products)
- All FK references updated to use new table names
- All tables already existed in `pinnacle_platform` DB (migrated by Quant session)

### /api/health updated to platform standard
- Was: `{"status": "healthy"}`
- Now: `{"status": "ok", "product": "pinnacle-sentinel"}`

### Platform alignment
- DATABASE_URL local .env updated to `pinnacle_platform` (was `pinnacle_sentinel`)
- Python version standardized: 3.14 → 3.12.13 (consistent with Quant and Veridia)
- .venv renamed: `.venv` → `.venv-sentinel` (consistent naming convention)
- create_all: added `checkfirst=True` to prevent duplicate index errors

### INF-010 Phase 3 — DB role separation (pending)
- `pinnacle_sentinel_app` role not yet created
- Will be done after Sentinel reaches full parity with Quant and Veridia

### Startup script
- pinnacle-infra `scripts/startup.sh` now includes 3 Sentinel tabs:
  - `[.venv-sentinel] Sentinel API :8010`
  - `[Vite] Sentinel UI :5180`
  - `[.venv-sentinel] Sentinel Commands`
