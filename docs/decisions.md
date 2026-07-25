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
