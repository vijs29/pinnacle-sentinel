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


## D-017 -- Ansible deploy gap found + fixed; shared-content architecture decided (2026-07-29)

### Real gap found in existing production deployment automation

Investigating why Sentinel's Methodology/NavBar/Infrastructure UI
changes weren't in production yet led to discovering pinnacle-infra
(a separate Ansible repo, already built with working roles for all
three products -- pinnacle_quant, pinnacle_veridia, pinnacle_sentinel,
plus common/postgres roles and a real deploy.yml/setup.yml/rollback.yml).

Found a real, live problem before running it against production: all
three roles' git-pull tasks use plain unauthenticated HTTPS
(`https://github.com/vijs29/{repo}.git`), and vault.yml has no
git-credential variable at all. Confirmed via a --check --diff dry run
against Sentinel specifically: the dry run succeeded (showed a real,
correct diff), but a direct check of the actual EC2 git remote showed
it had ALREADY been silently reset to plain HTTPS -- overwriting the
manually-configured SSH deploy key (github-sentinel alias) set up
earlier this same session. Ansible's git module enforces the remote to
match what's specified in the role, even during some check-mode runs.
This means any future deploy (manual or automated) touching Sentinel's
private repo would fail without a real fix -- not a hypothetical risk,
an active one.

**Decision**: rather than re-fix the remote manually (Ansible would
just silently overwrite it again next run), fix the ROLE itself. Vijay
chose ONE fine-grained GitHub Personal Access Token (Contents:
read-only), scoped to all three product repos, stored in vault.yml as
vault_github_token, over separate per-repo tokens/SSH keys. Tradeoff
made explicit and accepted: simpler to manage, but a single point of
compromise affects all three repos, unlike the individually-revocable
per-repo SSH deploy keys used elsewhere (Sentinel, RAQA). Vault token
added; role task updates to use it -- IN PROGRESS, not yet applied to
all three roles' git tasks as of this writing.

### Shared-content architecture decision

Separately, comparing today's real work against FOUNDER_OPERATING_MANUAL.md
and PLATFORM_INTEGRATION.md (both uploaded from Quant's repo) surfaced a
real, structural staleness problem: Quant's own Infrastructure.jsx page
(copied verbatim into Sentinel earlier today) shows Ansible as "in
progress" with every item marked "planned" -- but pinnacle-infra's
roles, discovered today, are real and already working. The page was
stale the moment it was copied, and will drift further every time any
one product's copy gets edited without the others.

**Decision**: pinnacle-infra becomes the single source of truth for
content shared across all three products -- FOUNDER_OPERATING_MANUAL.md,
PLATFORM_INTEGRATION.md, and the Infrastructure page's actual content --
templated into each product repo by Ansible AT DEPLOY TIME, the same
mechanism already used for .env generation from vault variables.
Deliberately NOT live runtime API calls between products (e.g. Sentinel
fetching Quant's own infrastructure content at page-load): that would
create a live cross-product dependency, directly conflicting with
FOUNDER_OPERATING_MANUAL.md's own fail-silent principle (Section 5) --
a product page should never break because a DIFFERENT product's server
is briefly unavailable. Vijay confirmed this direction; NOT YET BUILT --
scoped as its own follow-up task, deliberately sequenced after today's
documentation updates per Vijay's explicit instruction ("update
documents before attempting the tasks").

### Other real discrepancies found, flagged as open (not resolved here)

1. **Six-Stage Signal Gauntlet gap**: FOUNDER_OPERATING_MANUAL.md states
   "No signal goes LIVE without passing all six stages. There are no
   exceptions." None of Sentinel's 12 built flags have been through
   walk-forward backtesting, factor-model validation, or forward
   validation -- only real-filing data-extraction has been verified.
   By the Manual's own definition, these flags are deployed but not
   "LIVE." Flagged in strategy.md; not resolved -- needs Vijay's
   explicit call on how to treat currently-deployed-but-unvalidated
   flags.
2. **Brand color conflict**: FOUNDER_OPERATING_MANUAL.md specifies
   Sentinel's accent as #dc2626. Actual deployed code uses #d4443f --
   Vijay's own explicit choice earlier this session when offered both.
   Real, live discrepancy between the written standard and current
   practice. Not resolved -- needs an explicit decision on which is
   correct going forward, not a silent pick either way.
3. **Veridia accent conflict**: #0d9488 (teal) per FOUNDER_OPERATING_MANUAL.md
   vs #1d9e75 (green) used elsewhere (RAQA homepage work). Same kind of
   unresolved discrepancy, affecting a different product -- flagged
   here since it surfaced during this same document-comparison pass,
   not Sentinel's to unilaterally resolve.
4. **NavBar dropdown standard overgeneralized**: FOUNDER_OPERATING_MANUAL.md's
   Section 8 states every product needs "NavBar with all dropdowns
   (Research, Tools, Analysis, Infrastructure)" -- these are literally
   Quant's own dropdown names, stated as a universal requirement that
   doesn't fit Sentinel's real content (Screener/Methodology/Watchlist).
   The Manual itself likely needs correcting to state the REQUIREMENT
   (product-relevant dropdowns + a shared Infrastructure dropdown)
   rather than Quant's specific implementation as if universal.
5. **Missing required scripts**: FOUNDER_OPERATING_MANUAL.md Section 4/6
   reference verify_deploy.sh and session_start.sh as required tooling.
   Neither exists in Sentinel's repo. Not built.


## D-017 (continued) -- Consolidated single pinnacle_product role built and verified (2026-07-30)

Per Vijay's direction, consolidated the three near-duplicate roles
(pinnacle_quant, pinnacle_veridia, pinnacle_sentinel) into ONE
parameterized role (roles/pinnacle_product/), invoked three times from
deploy.yml with per-product variables pulled from group_vars/all/vars.yml's
existing products: list (which already had the right shape -- name,
port, subdomain, compose_dir -- just wasn't being used by the actual
role files; extended with repo, env_template, and compose_file fields).
Explicitly designed to support future products (QuantInfra AI,
Biosignal, etc.) with only a new vars.yml list entry + a new
{name}.env.j2 template + a ~6-line deploy.yml block -- the role itself
needs zero changes. --tags quant/veridia/sentinel selective-deploy
behavior preserved exactly, since each invocation keeps its own tag
(Option A -- explicit per-product blocks in deploy.yml referencing
centralized data -- chosen over a fully dynamic loop, which would have
required replacing --tags with --extra-vars and changed Vijay's daily
deploy commands).

Also fixed the D-017 git-auth gap as part of this: the role's git-pull
task now uses vault_github_token (one shared fine-grained PAT, Contents
read-only, scoped to all three repos) instead of unauthenticated HTTPS.

**Real incident during this work, documented per the Founder's
Manual's own honesty standard**: the GitHub PAT was accidentally pasted
in plaintext during a troubleshooting exchange (a vault edit attempt
failed silently because $EDITOR was unset, dropping the paste into the
bash prompt instead of an editor buffer, which surfaced the token in
plaintext). Token was immediately revoked and regenerated before any
further use. Root cause fixed by explicitly setting $EDITOR=nano before
retrying -- worth carrying forward as a checklist item for any future
vault-edit session on a fresh terminal.

**Second real bug found via the dry-run process itself**: initial
consolidated role hardcoded docker-compose.prod.yml for all three
products, but Veridia deliberately uses a DIFFERENT compose file
(docker-compose.web.yml -- the read-only public API service, kept
separate from docker-compose.yml's daily ledger-writing cron job as a
safety boundary, per earlier design). Caught by an actual --check
--diff dry run failing with a real "Cannot find Compose file" error,
not assumed away. Fixed by adding compose_file as a per-product
variable (vars.yml) rather than renaming Veridia's file to match the
others for consistency -- the file split itself is intentional and
meaningful, not accidental duplication like the three roles were.

**Verified**: all three products (--tags quant, --tags veridia,
--tags sentinel) now pass a full --check --diff dry run cleanly --
ok=8, changed=3, failed=0 each, confirming real task execution (config
generation, git pull, container deploy, health check all present), not
silently skipped. NOT yet run for real against production -- dry-run
verification only as of this writing; a real run is the natural next
step once Vijay confirms readiness.


## D-017 (continued) -- Real finding: production Ansible automation had never been committed to git (2026-07-30)

While preparing to commit the consolidated pinnacle_product role,
`git status` in pinnacle-infra revealed only ONE prior commit existed
("Initial scaffold," 2026-07-29) -- and it contained only .gitignore,
ansible.cfg, vars.yml, inventory/production.yml, requirements.yml, and
the common role. Confirmed via `git show --stat HEAD`.

Everything else -- the three original per-product roles' actual
tasks/handlers/templates, the postgres role, ALL THREE playbooks
(deploy.yml, setup.yml, rollback.yml), and group_vars/all/vault.yml
(every production secret: postgres password, veridia_ro/sentinel_ro
passwords, Pushover keys, Alpaca API keys, JWT secret, and today's new
GitHub token) -- had never been committed. This real, working,
actively-deploying production automation existed ONLY on Vijay's local
Mac disk, with zero backup, for the life of the project until this
session.

Confirmed .gitignore was correctly configured throughout (.vault_pass
-- the actual decryption password -- properly excluded; vault.yml
correctly NOT excluded, since it's encrypted and meant to be committed
per its own header comment) -- so this was a real gap in what got
committed, not a security misconfiguration.

**Fixed**: deleted the three old, now-superseded per-product role
directories (replaced by the consolidated pinnacle_product role, see
above) before this repo's first substantive commit, so the initial
real commit reflects the clean, current architecture rather than
carrying dead code forward. Committed everything else -- playbooks,
postgres role, pinnacle_product role, encrypted vault.yml -- in one
commit, pushed to github.com/vijs29/pinnacle-infra. This deployment
automation now has a real backup for the first time.

**Not yet done**: pinnacle-infra has no docs/ folder of its own
(decisions.md, journal.md, strategy.md) -- this whole D-017 arc has
been documented in SENTINEL's docs instead, since the investigation
started there, even though the actual changes are cross-product
infrastructure work. Worth deciding whether pinnacle-infra needs its
own documentation set, rather than continuing to track its own
decisions inside one product's docs by convention.


## D-018 -- First real Ansible deploy ever run: 7 real bugs found and fixed, Sentinel genuinely live (2026-07-30)

Ran the consolidated pinnacle_product role for real against production
for the first time (previously dry-run verified only). This was
genuinely the FIRST time pinnacle-infra's automation had ever been
exercised for real, for any product -- confirmed earlier the same day
that the whole repo had never even been committed to git until this
session. Every bug below was a real, previously-undiscovered defect
in automation that looked complete on paper.

**Seven real, distinct root causes found and fixed, each verified
against real production behavior, not assumed:**

1. **Git auth gap** -- unauthenticated HTTPS clone with no vault
   credential, silently overwriting a manually-configured SSH deploy
   key on the server. Fixed with one shared, fine-grained GitHub PAT
   (Contents: read-only) in vault.yml.
2. **Veridia's compose file** -- role assumed docker-compose.prod.yml
   for all three products; Veridia deliberately uses
   docker-compose.web.yml as a safety boundary (D-006, keeps the
   ledger-writing cron path separate). Fixed via a per-product
   compose_file variable.
3. **Health check networking** -- checked http://localhost:{port} from
   the EC2 HOST, but docker-compose.prod.yml deliberately uses
   `expose:`, not `ports:` (confirmed the SAME pattern exists for
   Quant too -- platform-wide, not Sentinel-specific). This check could
   never succeed regardless of container health. Fixed by checking
   from INSIDE the container via `docker compose exec`. Also discovered
   check_mode gap: the original uri-based check was silently SKIPPED
   during every --check --diff dry run all day, meaning no dry run had
   ever actually tested it -- added check_mode: false so future dry
   runs catch this class of bug for real.
4. **SECRET_KEY naming mismatch** -- Sentinel's own app/core/config.py
   reads SECRET_KEY specifically (no fallback); the vault template
   generated JWT_SECRET instead, crashing the app on every real
   startup. Sentinel-specific (Quant's own code expects JWT_SECRET and
   is fine) -- fixed only sentinel.env.j2, not the shared pattern.
5. **Stale vault Postgres password** -- vault_postgres_password had
   never matched the real, live password (since this automation had
   never run for real before). Fixed via a purpose-built script that
   fetches the real value from Quant's live .env and updates the vault
   directly, verified via SHA-256 hash comparison throughout --
   plaintext value never displayed or logged at any point.
6. **build: policy silently reusing a 2-day-stale image** -- confirmed
   via `docker images` (real image build timestamp, not container
   creation time, which is misleadingly recent on every deploy
   regardless of whether the image itself was rebuilt) that the
   deployed image was built 2026-07-28, TWO DAYS before any of today's
   work. Every "successful" deploy today had silently never rebuilt
   the image -- meaning today's Dockerfile port fix AND the
   Methodology/NavBar/Infrastructure UI changes were never actually
   live despite apparently-successful runs. Fixed: build: policy ->
   build: always.
7. **Caddy running 28 hours without a reload** -- Caddyfile on disk
   was completely correct (all three products), but the running Caddy
   process's own logs showed it only knew about quant.pinnacletranscore.com
   -- config on disk being correct doesn't mean the running process
   picked it up. The roles/caddy/ directory had been scaffolded empty
   and never built out (same pattern as everything else found today).
   Built a real caddy role: generates the whole Caddyfile from
   vars.yml's products list (a future product needs only a new list
   entry, never manual Caddyfile edits) with a reload handler, tagged
   'always' so it runs regardless of which product's --tags a deploy
   targets.
8. **Handler restart race condition** -- the .env template and git-pull
   tasks both notify a restart handler, which fires at the normal
   Ansible flush point (end of role/play) -- meaning it could fire
   AFTER "Wait for healthy" already passed, restarting the container
   again right before Caddy's public-endpoint verification ran.
   Confirmed via a real run: internal health check passed, Caddy then
   got connection-refused moments later reaching the same container.
   Fixed with an explicit `meta: flush_handlers` before the health
   check, guaranteeing verification always checks the final, settled
   state.

**Tooling change made mid-session**: installed ansible-core and
ansible-lint directly in Claude's own sandbox (via the MCP connector
discovery flow, after Vijay asked whether Claude could be given
testing ability) -- used for real, catching genuine correctness issues
(no-changed-when on the health check, FQCN module names, var-naming
convention) before shipping fixes, not just guessed-at. Does not
provide functional/runtime testing (no Docker/EC2 access in the
sandbox), but meaningfully raises the floor on avoidable static-
analysis-catchable bugs going forward.

**Final verified state**: PLAY RECAP failed=0. Confirmed live directly:
`https://sentinel.pinnacletranscore.com` returns 200,
`/api/health` returns `{"status":"healthy"}`. This deploy included a
genuine full rebuild (bug #6's fix), so today's earlier UI work
(Methodology page's Platform Integration section, NavBar's
Infrastructure dropdown, the port fix) are NOW actually live for the
first time, not just committed.

**Not yet done**: same fixes (health check, build:always, caddy role)
apply automatically to Quant and Veridia too via the shared
pinnacle_product/caddy roles, but neither has been redeployed with
these fixes yet -- only verified for Sentinel specifically. The
cross-product container rename (app/veridia-app/sentinel-app ->
pinnacle-quant/veridia/sentinel, already in TODO.md) remains separate,
deliberately not folded into this same change.


## D-018 (continued) -- Quant's .env deletion risk fixed and verified safe (2026-07-30)

Followed the exact plan from the earlier TODO.md entry. Fetched all 15
real secret values from Quant's live .env via a purpose-built,
no-plaintext-exposure script (same pattern as the Postgres password
fix -- values piped directly from an ansible ad-hoc fetch into a
script that only ever prints SHA-256 hash prefixes), added each to
vault.yml as vault_quant_<key>, verified all 15 landed correctly via
hash comparison. Then rewrote quant.env.j2 to reference all 15 vault
entries plus DOMAIN (not treated as a secret -- already a known,
non-sensitive Ansible variable).

**Safety-verified before any real deploy**: re-ran the --check --diff
dry run and checked the names-only redacted diff. Confirmed EVERY
removed line has a matching added line with the identical variable
name -- zero unexplained deletions. The 7 most sensitive variables
(ANTHROPIC_API_KEY, SECRET_KEY, all 4 Alpaca keys) showed no diff at
all, meaning the freshly-vaulted value is byte-identical to what's
already live -- the safest possible outcome. DATABASE_URL and
JWT_SECRET appeared as pure additions, not overwrites.

This closes the real, severe risk found earlier (a real deploy would
have deleted 16 live variables with no replacement, breaking Quant's
LLM access, auth, and all trading functionality). Real deploy for
Quant is next, now backed by actual verification rather than
assumption -- including correcting course after "Quant Claude" (a
separate Claude session on the Quant side) reported Quant as "ready to
deploy" without this verification having actually been confirmed at
that point in this conversation.
