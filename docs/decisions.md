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
