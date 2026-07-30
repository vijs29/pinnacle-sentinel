# Pinnacle Sentinel — Decisions Log

> This is the binding record of *why* the project is built the way it is.
> Every entry is dated. Decisions are appended, never silently rewritten.
> If a decision is reversed, add a new entry that supersedes the old one and
> say so explicitly -- do not delete history. (Same append-only ethos as
> Pinnacle Veridia's decisions.md.)

---

## D-001 -- Product identity (2026-07-20)

**SKU name: Pinnacle Sentinel.** A new SKU under the Pinnacle Platform
(RAQA Consultancy LLC). SEC filings monitoring product for early red-flag
detection, positioned toward short sellers and retail/prosumer investors.
Own repository (github.com/vijs29/pinnacle-sentinel), separate from
Pinnacle Quant and Pinnacle Veridia.

## D-002 -- What the product is (2026-07-20)

Pinnacle Sentinel detects five structured, Tier-1 red flags in SEC filings
across a stock universe, scores them via a confluence model (1 flag =
WATCH, 2+ flags on the same company = ALERT), and will eventually validate
whether flagged companies actually underperform afterward (T+30/90/180/365
vs SPY) -- the same "prove the claim, don't just assert it" philosophy as
Pinnacle Quant and Pinnacle Veridia.

**The five Tier-1 flags (v1 scope, structured data only, no NLP):**
- Late filing (NT 10-K / NT 10-Q) -- existence of the filing itself is the flag.
- Auditor change (8-K Item 4.01, and Item 4.02 when auditor-related).
- CFO resignation (8-K Item 5.02, keyword-decided on the body text).
- Material weakness (8-K Item 4.02 when weakness-related, or 10-K).
- Accelerated insider selling (Form 4, requires a per-insider historical
  baseline -- NOT yet built as of this doc, see journal.md).

Going-concern disclosure was considered for v1 but deferred to v2 -- it
requires NLP/footnote extraction, unlike the five structured flags above.

## D-003 -- Target audience and go-to-market priority (2026-07-20)

Evaluated audiences, in order of fit:
1. **Short sellers / activist researchers** -- highest willingness to pay;
   signal decays fast once public, so early detection has real value.
2. **Retail/prosumer investors** -- natural cross-sell to Pinnacle Quant's
   existing user base; same user, adjacent signal type.
3. **Small hedge funds / RIAs** -- underserved tier, priced out of
   Bloomberg/FactSet-level filing monitoring but too sophisticated for
   free EDGAR search alone.
4. **Financial journalists / independent newsletter writers** -- smaller
   individual budgets, large addressable count.
5. **Compliance/legal teams at public companies** -- defensive/competitive-
   intelligence use case, different (B2B) buyer profile, not trading-motivated.

**Go-to-market decision: retail/prosumer investors and short sellers**,
both reachable through Pinnacle Quant's existing distribution rather than
a new sales motion.

**Open question, not yet decided:** product shape differs by audience -- a
retail-investor "filing confluence score" vs. a short-seller-focused
footnote/red-flag scanner are different products wearing the same data
pipe. Needs an explicit decision on which to build first once the
confluence scorer exists.

## D-004 -- Architecture reuse from Pinnacle Quant (2026-07-20)

Deliberately reuses proven patterns rather than reinventing:
- **Confluence scoring engine** -- score multiple weak filing-level signals
  together (e.g. insider selling + auditor change + late filing) rather
  than alerting on any single event in isolation. Same 1-flag=WATCH,
  2+=ALERT pattern as Quant's confluence-path design.
- **Independent validation/reconciliation loop** -- track whether flagged
  filings actually preceded a material price move, so the system doesn't
  grade its own homework. Mirrors Quant's Alpaca-vs-platform reconciliation
  discipline.
- **Dedup'd notification/alerting layer** -- reuse Quant's Pushover
  infrastructure pattern for filing-event alerts once flags are
  alert-worthy.
- **Regime-aware backtesting is explicitly NOT directly reusable** here --
  filings don't have a market-volatility "regime" concept the same way
  price signals do. Would need rethinking as sector- or filing-type-specific
  backtesting instead, if pursued.

## D-005 -- EDGAR data source: submissions API, not full-text search (2026-07-21)

SEC's full-text search API (efts.sec.gov) is best suited to cross-company
keyword scans (e.g. searching all filings for "going concern" -- needed for
the deferred v2 NLP flag). For v1's actual need -- "give me all filings of
form type X for CIK Y since date Z," polling per-company across a fixed
universe -- the **submissions API** (data.sec.gov/submissions/CIK##########.json)
is the better fit: free, no API key, standard per-company structured
polling pattern used by most production EDGAR integrations.

## D-006 -- Universe: S&P 500 via Wikipedia, Russell 1000 abandoned (2026-07-21)

Originally planned to include Russell 1000 via iShares' IWB holdings CSV.
**Abandoned after confirming Akamai Bot Manager blocks scripted access**
(confirmed via session cookies: bm_s, bm_so, bm_ss -- Akamai's
signature bot-detection cookies). Getting past this would require a
headless browser (Playwright) and ongoing maintenance risk against
Akamai's evolving challenges -- not worth it for what's only a weekly
universe-refresh job.

**Decision: S&P 500 only for v1**, sourced from Wikipedia's "List of S&P 500
companies" page -- a static HTML table, no anti-bot friction, and
conveniently already includes CIK numbers directly (skips a separate
SEC ticker-to-CIK lookup step entirely). Russell 1000 expansion deferred
indefinitely; if revisited, expect the same Akamai obstacle and plan for
Playwright from the start rather than re-discovering the blocker.

## D-007 -- Schema: normalized Filing/FlagEvent/SentinelOutcome (2026-07-21)

Considered two designs for how filings and detected flags relate:
1. A single flat table with flag data as columns directly on Filing
   (confluence_score, flag_type, outcome_30d, etc. all on one row).
2. Separate tables: Filing (raw filing metadata) + FlagEvent (a
   detected flag, one row per flag) + SentinelOutcome (grading per flag
   per horizon).

**Decision: separate, normalized tables (option 2).** Matches the
validation plan directly -- flags need to be graded independently at
T+30/90/180/365, so they need their own row per flag-event, not squashed
into Filing columns. A single filing can produce zero, one, or multiple
flags, which the confluence model (WATCH vs ALERT) depends on counting
correctly; that's awkward to represent in a flat single-row-per-filing
design.

(An earlier flat-schema stub existed briefly on disk from initial
scaffolding before this decision -- superseded, not used. A stray copy of
that old stub was later found accidentally inside the Pinnacle Quant repo
and deleted from there as unrelated cross-project debris, 2026-07-22.)

## D-008 -- 8-K flag classification: keyword-decided on stripped body text (2026-07-21)

Item 4.02 covers both auditor-change-related non-reliance restatements AND
material weakness disclosures -- the same item code, two different
meanings. Decision: classify by keyword match in the item's text (searching
for material-weakness-specific vs auditor-specific terms) rather than
flagging both or picking one arbitrarily.

Item 5.02 covers CFO resignations but ALSO routine officer/director
appointments, board elections, and other personnel changes unrelated to a
resignation -- classifying on the full item text (including its standard
boilerplate heading, which always contains words like "departure" and
"appointment" regardless of actual content) produced a real false positive:
a filing about RTX's CFO joining 3M's board was flagged as 3M's own CFO
resigning. **Fixed: strip the boilerplate heading line before keyword
matching**, so classification only runs against the actual body text
describing what happened. Verified via a before/after test batch (5 flags
-> 2 correct flags after the fix).

---

## Open questions (carried, not yet decided)

- Retail-investor "confluence score" product vs. short-seller-focused
  footnote/red-flag scanner -- which to build first (see D-003).
- Whether/how to handle Russell 1000 coverage if ever revisited (see D-006).
- Exact confluence scoring formula beyond the simple 1=WATCH/2+=ALERT rule
  -- not yet decided, awaits the accelerated-insider-selling detector
  (the highest-value flag) actually existing.
- Outcome validation methodology details (which benchmark, which costs
  model) -- should probably borrow Quant's cluster-robust, net-of-cost
  testing discipline established 2026-07-21/22, rather than reinvent it
  less rigorously.

## D-009 -- Scope expansion: comprehensive Category 1 + Category 2 coverage (2026-07-26)

SUPERSEDES D-002's five-flag boundary. Original v1 scope (late filing,
auditor change, CFO resignation, material weakness, accelerated insider
selling) was an arbitrarily-bounded starting subset, not a considered
final scope. Corrected scope is comprehensive coverage across both
categories used in real forensic/short-seller research:

Category 1 (disclosure/text-based, expanded): the original five, plus
going-concern language (previously deferred to v2 per D-002 -- now in
scope), financial restatements, related-party transaction changes,
revenue recognition policy changes, accounting method changes, debt
covenant violation language, SEC investigation/subpoena/whistleblower
mentions, executive compensation red flags (DEF 14A).

Category 2 (financial ratio/XBRL-based, new): Beneish M-Score (8
variables), Altman Z-Score (5 variables), Sloan accruals ratio, plus
individual ratios (OCF/NI divergence, DSO trend, inventory turnover,
capex/depreciation, receivables growth vs revenue growth, debt trends).

Existing built work (8-K/NT detectors, current schema) is superseded
where it conflicts with the rework below -- scrapping/reworking is
accepted as the cost of getting scope right, per explicit instruction
2026-07-26.

## D-010 -- New data domains and sources (2026-07-26)

- XBRL structured financials: data.sec.gov/api/xbrl/companyfacts/
  CIK##########.json, per-company, no API key -- same polling pattern
  as existing submissions-API ingestion (D-005).
- DEF 14A (proxy statements): via existing submissions-API ingestion,
  new form type added to the target list.
- Full 10-K/10-Q text: extracted sections only (audit opinion,
  related-party footnote, revenue-recognition note, debt covenant
  language), NOT full documents -- storage volume consideration, see
  D-011.
- Market cap history (price x shares outstanding): reuse Pinnacle
  Quant's yfinance pipeline rather than build a second price feed --
  needed only for Altman Z-Score's X4 variable.
- SEC full-text search (efts.sec.gov): reintroduced, previously deferred
  in D-005 for a different reason (per-company polling was the v1 need);
  now the right tool for cross-company keyword scans (going-concern,
  restatement, investigation language).

## D-011 -- Schema rework: FinancialFact, QuantScore, FlagEvent.source_type (2026-07-26)

Original Filing/FlagEvent/SentinelOutcome schema (D-007) assumed every
flag traces to a single discrete filing event -- breaks for Category 2,
where scores/ratios are computed across multiple periods of financial
data, not one filing.

New tables:
- FinancialFact: (cik, concept, unit, period_end, fiscal_year,
  fiscal_period, value, form_type) -- local mirror of SEC XBRL
  companyfacts structure.
- QuantScore: (cik, period_end, score_type, value, component_json) --
  stores composite scores WITH underlying component variables, not just
  the final number, so scores are auditable the same way the
  cfo_resignation investigation (2026-07-25) audited a text classifier.

FlagEvent gets a new source_type column (disclosure | quantitative) so
confluence scoring can sum across both flag categories consistently.

Full 10-K/10-Q text: store extracted relevant sections only, not full
documents -- full-document storage across 503 companies x multiple
years would bloat local Postgres significantly; EDGAR URL retained as
source-of-truth pointer.

## D-012 -- flag_detector_8k.py sentence-boundary fix, revisited in this rework (2026-07-26)

The naive ". "-based sentence-splitting bug found and reverted 2026-07-25
(AOS false-negative from "A. O. Smith" abbreviation) is addressed now as
part of this broader rework rather than deferred further -- switch to a
real sentence tokenizer or fixed-character keyword window. Also revisits
the still-unverified precision of auditor_change and material_weakness
flagged in the 2026-07-25 journal entry.


## D-013 -- Known limitation: Altman Z-Score understated for split-history companies (2026-07-26)

Altman Z-Score's market-value-of-equity term (price x shares outstanding)
uses CommonStockSharesOutstanding as-reported per filing, not adjusted for
stock splits that happen after that filing date. yfinance's price series
is always split-adjusted regardless of settings, so pairing it with the
as-reported share count understates market value of equity -- and
therefore the Z-Score -- for any pre-split fiscal year, for any company
that has split its stock since. Confirmed via TPL (two 3-for-1 splits,
2024 and 2025).

Attempted fix (scale share count by cumulative split ratio) worked for
clean multi-way splits but broke on companies with spin-offs in their
history -- yfinance records spin-off price adjustments in the same
'Stock Splits' data field as genuine splits (e.g. MMM's 2024 Solventum
spin-off appears as a 1.196 "split", not a real share-count change),
and there's no reliable way to distinguish the two from yfinance's data
alone without further work. Reverted rather than ship a partial fix.

**Decision: leave as a known, disclosed limitation for now.** Sloan and
Beneish M-Score are unaffected (no market-price dependency). Altman
Z-Score remains usable, with the understanding that split-history
companies' pre-split-year scores run low relative to their true value.
Revisit only with a more rigorous approach (e.g. cross-referencing
actual "stock split" 8-K filings, already ingested, to distinguish real
splits from spin-off artifacts) if Altman precision becomes a priority.


## D-014 -- Known limitation: related_party_change detector not reliable, disabled (2026-07-28)

Built related_party_detector.py against DEF 14A (Item 404 of Regulation
S-K), after the original 10-K Item 13 attempt failed outright (large-cap
filers almost universally "incorporate by reference" to the proxy,
leaving no real content in the 10-K itself -- confirmed via AWK, AIG,
AMCR, MO, AEE).

DEF 14A version went through 4 real fix rounds, each solving a genuine,
distinct problem: (1) wrong section instance (grabbed the table-of-
contents mention, not real content -- fixed by taking the LAST heading
occurrence); (2) naive entity extraction caught debt-instrument/product/
regulator names (MRK's own drug Keytruda, IDEXX's own product, the EPA)
-- fixed by requiring a name + dollar figure + explicit relationship
word in the same sentence; (3) boilerplate subsection headings ("Other
Transactions") caught as fake names -- fixed via targeted stopwords;
(4) lowercase mid-sentence POLICY references (describing the approval
process, not actual transactions) matched as if they were the real
section heading -- fixed by requiring the heading match to be
capitalized in the source.

Did NOT converge. Final round (spot-checked before shipping, not
after) still showed: whitespace/table-of-contents artifacts as fake
entities (CPRT); the FILER'S OWN NAME mangled by HTML-to-text spacing
("Con \n\n\nEdison") caught as a newly-discovered related party of
itself (ED); and, the real remaining root cause -- "beneficial owner"/
"beneficially owns" are the SAME phrases used in the mandatory,
routine Security Ownership table (listing officer/director share
counts, present in every proxy, never a red flag) as in genuine
related-party narratives. This confound sits underneath the entity-
extraction approach as designed and was not resolved.

**Decision: flag_events.related_party_change is NOT populated in
production.** All test-run flags deleted. The detector code remains in
the repo (app/services/related_party_detector.py) as a documented,
honest attempt -- not wired into scheduler_service.py, not run against
the full universe. Revisit only with a fundamentally different
approach (e.g. explicitly locating and excluding the Security Ownership
table by its own distinct heading before running relationship-word
matching, or a real NLP/LLM-based extraction instead of regex
heuristics) if this becomes a priority again.


## D-015 -- Known limitation: say_on_pay_failure detector not reliable, disabled (2026-07-28)

Built executive_comp_detector.py against 8-K Item 5.07 (Submission of
Matters to a Vote of Security Holders), targeting Say-on-Pay approval
percentage as a real, verifiable numeric signal (deliberately NOT
DEF 14A compensation-discussion prose, to avoid D-014's fragility).

Extraction logic went through 5 real fix rounds, each verified against
REAL 8-K filings (Micron, eBay, Eastman Chemical, Chevron, A.H. Belo,
AsiaInfo, Zoom Telephonics, plus MMM's actual 2024 say-on-pay failure
found via a live database spot-check -- 45.31% approval, shareholders
explicitly "did not approve"):
1. Original symmetric before/after window bled backward into an
   EARLIER, unrelated proposal (V's director-election vote percentage
   wrongly grabbed as say-on-pay data).
2. Bare "for" matched ordinary English prose ("accounting firm for
   2026") as if it were a vote-table label.
3. Case-sensitivity bugs when tightening the FOR-label pattern (broke
   real "Votes For" Title Case matches while fixing the false positive).
4. Missing support for the "labels-block-then-numbers-block" table
   style (FOR/AGAINST/ABSTAIN listed together, THEN all their numbers
   together in the same order) -- this format caused MMM's real 2024
   failure to go completely undetected under the original logic.
5. Added block-table support, but this surfaced the ROOT, unresolved
   problem: MMM's real filing contains MULTIPLE FOR/AGAINST/ABSTAIN
   tables in the same document (say-on-pay proposal, a separate
   shareholder proposal, AND director-election results each use this
   identical table structure) -- the detector cannot reliably
   distinguish which table belongs to the say-on-pay proposal
   specifically vs. an adjacent, differently-purposed proposal. Final
   verified check: still matched 93.99% for MMM's 2024 filing instead
   of the real 45.31% -- a DIFFERENT wrong table, not the intended one.

Also observed clearly implausible percentage-method results even after
fixes (SW 0.31%, OXY 2.72%, ACGL showing the IDENTICAL 6.75% across two
different fiscal years -- a strong signal of the same class of bug,
matching an unrelated nearby percentage rather than the real say-on-pay
outcome specifically).

**Root cause, unresolved**: correctly associating a vote-count table
with the SPECIFIC proposal it belongs to, when a single 8-K commonly
contains several near-identical-looking tables for different proposals
(director elections, auditor ratification, shareholder proposals,
say-on-pay) side by side. Proximity-based window search cannot reliably
disambiguate these. Would need the document parsed into distinct
"Proposal No. X" sections FIRST, then searched within each section
independently -- a real structural redesign, not a regex patch.

**Decision: flag_events.say_on_pay_failure is NOT populated in
production.** All test-run flags deleted. Detector code remains in the
repo (app/services/executive_comp_detector.py) as a documented, honest
attempt with real partial value (the core numeric-signal concept is
sound, several genuine extraction-format bugs were found and fixed) --
not wired into scheduler_service.py, not run against the full universe.
Revisit only with the proposal-section-boundary-aware redesign
described above.

**Category 1 status**: 9 of the original 7+2 = ~9 target flag types
built and trusted in production (late filing, auditor change, CFO
resignation, material weakness, debt covenant violation, financial
restatement, going concern, SEC investigation/subpoena/whistleblower,
revenue recognition change). Two attempted and honestly disabled:
related_party_change (D-014), say_on_pay_failure (D-015) -- both
represent real signal concepts worth revisiting with more careful
document-structure-aware approaches, not abandoned ideas.


## D-016 -- Insider selling cluster: ingestion built, cluster-detection logic still pending (2026-07-29)

Built app/models/insider_transaction.py (new insider_transactions table)
and app/services/form4_ingest.py -- the last of the original 5 Tier-1
flags never actually parsed from real data (285,306 Form 4 filing
REFERENCES were ingested weeks ago, but zero transaction details --
shares, price, transaction code -- were ever extracted).

Verified real Form 4 XML schema against two real filings (Ameren/AEE,
Warner Baxter, 2017-06-09; 3M/MMM, Jennifer Rumsey, 2026-06-05) before
writing the parser -- confirmed <nonDerivativeTransaction> elements are
the real transactions (vs <nonDerivativeHolding>, an informational
balance, deliberately excluded), transactionCode "S" = open-market sale
(the only code that should count toward a selling-cluster signal --
excludes G=gift, A=award/grant, M=option exercise, F=tax withholding),
and rptOwnerCik as the stable per-insider identifier (not name-text
matching, which varies in formatting -- confirmed "RUMSEY JENNIFER" vs
"BAXTER WARNER L" vs Title-Case variants across different filers).

Two real bugs found and fixed before trusting this at scale:
1. First attempt assumed a fixed URL transform (strip "/xslF345X03/"
   from the cached viewer-wrapper URL to get the raw XML). This broke
   on a large fraction of a 20-filing test batch ("mismatched tag" XML
   parse errors) -- traced to 3M's filings using a DIFFERENT viewer
   folder name (xslF345X06) and a different primary filename
   (form4.xml, not edgar.xml). Naming isn't fixed across filers/years.
2. FIXED via SEC's own index.json directory listing -- looks up each
   filing's real primary XML document dynamically rather than guessing
   a naming convention. Re-verified: 20/20 filings parsed successfully,
   zero failures of any kind, 42 real transaction rows created.

Spot-checked the real parsed data before trusting it: 8 MMM directors
correctly show identical share counts/prices for the same 2026-05-12
grant date (expected -- annual director equity grants are typically
identical dollar-value awards); a real employee's option-exercise ("M")
correctly produced two linked rows (exercise + resulting sale, standard
cashless-exercise pattern); a real open-market sale (Theresa Reinseth,
2026-02-11) correctly split into 5 transactions at slightly different
prices, matching how large sales commonly execute throughout a trading
day.

**Scale note**: 285,306 Form 4 filings x 2 requests each (index.json
lookup + XML fetch) is a genuinely long-running job -- estimated
2-3+ days of continuous runtime, unlike anything else ingested this
session. Launched in the foreground (Vijay's choice, wants live
visibility into progress/errors as it runs) rather than backgrounded,
in a dedicated terminal, with --rescan-all against the full 285K
backlog.

**NOT yet built**: the actual cluster-detection logic (querying
insider_transactions for multiple distinct insiders selling within a
30-day window per ticker) and the resulting FlagEvent creation
(flag_type="accelerated_insider_selling"). This is purely the
ingestion/parsing layer -- the detector itself is the next step, once
enough real data has accumulated to test cluster logic against.
