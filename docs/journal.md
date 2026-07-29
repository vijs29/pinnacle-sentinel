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
