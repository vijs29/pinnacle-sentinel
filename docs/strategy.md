# Pinnacle Sentinel — Strategy

> The "why this exists and why it can win" document. Decisions live in
> decisions.md; the running work log lives in journal.md. This file is the
> thesis and may be revised as understanding improves -- but revisions should
> be additive and dated, in keeping with the honesty ethos shared across the
> Pinnacle Platform.

---

## The one-paragraph thesis

Public companies leave a trail of structured, legally-mandated disclosures
long before their problems become obvious in the stock price or the news.
An auditor resigning, a CFO leaving abruptly, a late filing, a disclosed
material weakness in financial controls, or an executive suddenly
accelerating their own stock sales -- none of these alone proves fraud or
failure, but together, and early, they are a real and underused signal.
Pinnacle Sentinel watches SEC filings across a stock universe for exactly
these red flags, scores them by confluence (more simultaneous flags = more
significant), and will validate -- honestly, against real price outcomes --
whether flagged companies actually underperform afterward. The same
verify-don't-just-assert discipline that runs through Pinnacle Quant and
Pinnacle Veridia applies here: a red flag that doesn't predict anything is
a disclosed null result, not a hidden failure.

## Why this is a real, addressable gap

- **The data is free and already public** -- every flag comes from SEC
  EDGAR, a filing every public company is legally required to make. There
  is no proprietary data cost, no vendor lock-in on the input side.
- **The audience already exists and already pays for an edge.** Short
  sellers and activist researchers are the natural first market -- they are
  already comfortable paying for early information, and the value of these
  signals decays quickly once they become widely known, which rewards
  being first rather than requiring being the only source.
- **Underserved middle tier.** Bloomberg Terminal / FactSet-level filing
  monitoring exists, but it's priced for large institutions. Free EDGAR
  full-text search exists, but requires a human to know what to search for
  and to check it manually. Nothing serves the tier in between -- small
  funds, RIAs, and serious retail/prosumer investors who want systematic
  coverage without an enterprise price tag.
- **Natural cross-sell.** Pinnacle Quant already has a retail/prosumer user
  base interested in signal-driven investing. Sentinel is an adjacent
  signal type (company-health red flags instead of price/momentum
  technicals) reachable through the same distribution, not a new
  go-to-market motion.

## The moat, precisely

Not the raw data -- EDGAR is free and public, so anyone can technically
scrape the same filings. The moat is:
1. **Structured, systematic confluence detection** across an entire
   universe, continuously, rather than a human manually searching one
   company at a time.
2. **Honest, disclosed validation** of whether the flags actually predict
   anything -- the same T+30/90/180/365-vs-SPY grading discipline as
   Quant's signal validation, applied to filing-based red flags instead of
   price-technical signals. Most filing-alert services (if they publish any
   track record at all) don't publish this kind of rigorous, falsifiable
   backtest against real price outcomes.
3. **Confluence scoring** -- the insight that flags mean more together than
   apart. A late filing alone is common and often meaningless; a late
   filing plus an auditor change plus accelerated insider selling on the
   same company in the same window is a very different, much rarer signal.

## Proof methodology (planned, not yet built -- see decisions.md D-002)

Mirrors Quant's approach directly:
1. Detect flags on filings as they're ingested (already built for 4 of the
   5 Tier-1 flags: late filing, auditor change, CFO resignation, material
   weakness; accelerated insider selling remains).
2. Score confluence per company (1 flag = WATCH, 2+ = ALERT) -- not yet built.
3. Record price at flag date (T=0), then grade at T+30/90/180/365 against
   SPY -- track excess return, decline >10%/>20% thresholds, and the
   extreme case (bankruptcy/delisting within 365 days).
4. Publish the full track record, including flags that turned out to be
   noise -- a flag type that doesn't predict anything becomes a disclosed
   null result, exactly as PEAD and the original 12-signal technical suite
   were honestly rejected in Pinnacle Quant's own history.

## What would falsify this thesis (stated in advance)

- If, once validated, none of the five Tier-1 flags (individually or in
  confluence) show a statistically meaningful relationship with subsequent
  underperformance, that's a publishable honest finding about filing-based
  red flags in this universe -- not a failure to hide, the same posture
  Quant took toward its own rejected technical signals.
- If the target audience (short sellers, retail/prosumer investors) doesn't
  find systematic confluence detection more valuable than what they already
  do manually or via existing free EDGAR search, the moat may be real but
  the market may not be -- a go-to-market question, not an engineering one.

## Open, undecided product-shape question

A retail-investor-facing "filing confluence score" (simple WATCH/ALERT
badges, similar to Quant's signal badges) and a short-seller-facing
footnote/red-flag research tool (deeper detail, raw filing excerpts,
per-flag drill-down) are genuinely different products built on the same
underlying data pipeline. Which to build first is not yet decided --
carried as an open item in decisions.md.
