# Pinnacle Sentinel — Validation Methodology

## Purpose

This document describes how Pinnacle Sentinel detects, scores, and validates
SEC filing red flags. It is the technical and epistemic standard against which
every claim made by the product is measured.

The same verify-don't-assert discipline that runs through Pinnacle Quant and
Pinnacle Veridia applies here: a flag type that doesn't predict underperformance
is a disclosed null result, not a hidden failure.

---

## What Sentinel Claims (and What It Does Not)

**Claims:**
- Detects structured red flags in SEC filings across 503 S&P 500 companies
- 9 disclosure-based flags + 3 quantitative flags (12 total, all in production)
- Confluence scoring: 1 flag = WATCH, 2+ flags = ALERT
- 365,387+ filings ingested, 2,746 flag events detected

**Does NOT claim:**
- Any flag predicts underperformance — **none have passed the Six-Stage Gauntlet**
- Statistical validation — walk-forward backtests not yet run
- Trading signals — Sentinel is a red-flag detector, not a signal engine
- Live integration with Quant — planned but gated on Stage 4 validation

---

## Core Principles

1. **Detect, don't predict (yet)** — flag detection is built and verified. Prediction validation is next.
2. **Verify against real filings** — every detector verified against actual SEC EDGAR filings before deployment.
3. **Disclose limitations** — flags with unresolved root causes are disabled and documented (D-014, D-015).
4. **Gate on gauntlet** — no flag goes LIVE (publicly visible, integrated with Quant) without all six stages.
5. **Honest confluence** — scoring is additive, capped, and explained. No black-box scores.

---

## Flag Inventory (Current State, 2026-08-04)

### Category 1 — Disclosure-Based (9 flags)

| Flag | Source | Status |
|------|--------|--------|
| Late filing (NT 10-K / NT 10-Q) | Filing existence | ✅ Production |
| Auditor change | 8-K Item 4.01/4.02 | ✅ Production |
| CFO resignation | 8-K Item 5.02 | ✅ Production |
| Material weakness | 8-K Item 4.02, 10-K | ✅ Production |
| Debt covenant violation | 8-K text detection | ✅ Production |
| Financial restatement | 8-K text detection | ✅ Production |
| Going concern | 10-K footnote detection | ✅ Production |
| SEC investigation/subpoena | 8-K text detection | ✅ Production |
| Revenue recognition change | 8-K text detection | ✅ Production |

### Category 2 — Quantitative (3 flags)

| Flag | Method | Status |
|------|--------|--------|
| Beneish M-Score | 8 XBRL variables | ✅ Production |
| Altman Z-Score | 5 XBRL variables | ✅ Production |
| Sloan Accruals Ratio | XBRL accruals | ✅ Production |

### Disabled (2 flags, documented root cause)

| Flag | Root Cause | Decision |
|------|-----------|---------|
| Related-party transactions | Parser unreliable across filing formats | D-014 |
| Say-on-pay vote failure | Data not reliably structured in EDGAR | D-015 |

### In Progress (1 flag)

| Flag | Status |
|------|--------|
| Accelerated insider selling | Ingestion built (285K+ Form 4s), cluster-detection logic pending |

---

## Confluence Scoring

- 1 flag on a company in a rolling window → **WATCH**
- 2+ flags on a company in a rolling window → **ALERT**
- Score is capped at 12 (one point per distinct flag type, no double-counting)
- Score is additive — each flag contributes independently

---

## Six-Stage Signal Gauntlet

**None of Sentinel's 12 flags have passed any stage.** Current status:

| Stage | Description | Status |
|-------|-------------|--------|
| 1 | Hypothesis registration (falsifiable, written before data) | ⏳ Partially done via strategy.md |
| 2 | Walk-forward backtest (500+ samples, p<0.05) | ❌ Not started |
| 3 | Factor model validation (Fama-French alpha) | ❌ Not started |
| 4 | Forward validation (100+ graded live flags) | ❌ Not started (`sentinel_outcomes` table exists, nothing populates it) |
| 5 | Automated daily audit (20 consecutive clean days) | ❌ Not started |
| 6 | Honest track record publication | ❌ Not started |

**Until Stage 4 is reached:** flag data gated behind Vijay's account.
**Public visitors see:** "validation in progress" placeholder.

---

## Data Sources

- **SEC EDGAR submissions API** — 503 S&P 500 companies, 4 form types (8-K, NT 10-K, NT 10-Q, Form 4)
- **SEC EDGAR XBRL companyfacts API** — financial facts for quantitative scoring
- **No paid data sources** — EDGAR is free and public

---

## Outcome Grading (Planned)

When Stage 4 begins:
- Record price at flag date (T=0)
- Grade at T+30, T+90, T+180, T+365 vs SPY
- Measure: excess return, decline >10%/>20%, bankruptcy/delisting
- All outcomes stored in `pinnacle_sentinel_outcomes` table

---

## Known Limitations

1. **No flags validated** — detection built, prediction unproven
2. **CFO resignation precision** — keyword-based, some false positives (documented)
3. **Form 4 duplicate issue** — sequential-ID duplicate rows for some filings, root cause pending (D-019)
4. **NLP gap** — going concern uses footnote detection, not full NLP
5. **Universe limited to S&P 500** — 503 companies, not full market

---

## Platform Documentation (INF-014)

### The self-documenting platform

This product is one of four components in a self-documenting platform architecture.
Each product maintains its own `docs/FOUNDER_OPERATING_MANUAL.md` — the authoritative
record of how it is built, validated, deployed, and operated. Every night at 9pm ET,
an automated assembler reads all four documents and publishes a unified master document.

**The platform documents itself. No human assembles it. No human forgets to update it.**

The assembled master document is served through this product's
`/api/platform/founder-manual` endpoint (auth-gated) and is available to
authorized users via the Founder's Manual link in the Infrastructure dropdown.

### Why this matters

Distributed documentation drifts. A central document becomes a bottleneck.
The Pinnacle solution: each product owns its truth, the assembler owns the synthesis.
Edit this product's `docs/FOUNDER_OPERATING_MANUAL.md` and by 9pm ET tonight,
the master document reflects the change.

### Technical details

Full architecture, pipeline diagram, and design rationale documented in:
**Pinnacle Platform Hub → Methodology → The Self-Documenting Platform (INF-014)**

| Item | Detail |
|------|--------|
| Source file | `docs/FOUNDER_OPERATING_MANUAL.md` (this repo — edit here) |
| Assembled output | `pinnacle-platform-hub/docs/FOUNDER_OPERATING_MANUAL.md` (never edit directly) |
| DB table | `platform_founder_manual` (id=1, upserted nightly) |
| Endpoint | `GET /api/platform/founder-manual` (auth required) |
| Assembly schedule | Nightly 9pm ET via pinnacle-ops cron (INF-014) |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Aug 2026 | Platform Documentation section added (INF-014 self-documenting platform). |
| 1.0 | Aug 2026 | Initial methodology document. 12 flags documented, Six-Stage Gauntlet status, confluence scoring, known limitations. |
