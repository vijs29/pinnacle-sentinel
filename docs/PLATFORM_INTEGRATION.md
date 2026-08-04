# Pinnacle Platform — Cross-Product Integration Strategy

**Status:** Approved — July 26, 2026 (scoring model revised July 30, 2026)
**Author:** Pinnacle Platform / RAQA Consultancy LLC
**Version:** 1.1

---

## 1. Overview

The Pinnacle Platform consists of three independent products that share a common risk intelligence layer:

| Product | Question it answers | Primary user |
|---------|-------------------|--------------|
| **Pinnacle Sentinel** | What's wrong with this company? | Short sellers, forensic analysts |
| **Pinnacle Veridia** | How much risk is in this position? | Risk managers, quant traders |
| **Pinnacle Quant** | When should I act on this signal? | Retail investors, quant traders |

Each product is independently useful. Together, they form a composite risk filter that no single product can provide alone.

---

## 2. Architecture

```
+-------------------------------------------------------------+
|                    PINNACLE PLATFORM                         |
|                                                             |
|  +------------------+  +------------------+  +----------+  |
|  | PINNACLE SENTINEL|  | PINNACLE VERIDIA |  | PINNACLE |  |
|  |                  |  |                  |  |  QUANT   |  |
|  | SEC filings      |->| VaR models       |->| Price    |  |
|  | red flags        |  | per-ticker       |  | signals  |  |
|  | confluence score |  | forecasts        |  | scoring  |  |
|  +------------------+  +------------------+  +----------+  |
|         |                      |                  |         |
|         +----------------------+------------------+         |
|                                |                            |
|                       Composite Risk Score                  |
|                       shown to all users                    |
+-------------------------------------------------------------+
```

### Data flows

**Pinnacle Sentinel → Pinnacle Quant:**
Pinnacle Sentinel writes a daily flag summary per ticker. Pinnacle Quant reads it at scan time (1pm ET). If a ticker has active Pinnacle Sentinel flags, Pinnacle Quant's conviction is downgraded accordingly.

**Pinnacle Veridia → Pinnacle Quant (live — D-016):**
Pinnacle Veridia writes `ticker_var_forecast_latest.json` daily before Pinnacle Quant's 1pm scan. Pinnacle Quant reads it and downgrades BUY → WATCH when `wide_band=True`. Already deployed.

**Pinnacle Sentinel → Pinnacle Veridia:**
Pinnacle Sentinel flags often precede volatility spikes. Pinnacle Veridia uses Pinnacle Sentinel flag dates as context for VaR breach attribution — confirming whether a breach had a fundamental driver vs. pure market noise.

**Pinnacle Veridia → Pinnacle Sentinel:**
When a Pinnacle Veridia VaR breach coincides with a Pinnacle Sentinel red flag, Pinnacle Sentinel's composite score increases. The two signals are independent confirmation of the same underlying risk.

---

## 3. Composite Risk Score

### Definition

The composite risk score is a number from 1 to 12 that combines inputs from Pinnacle Sentinel, Pinnacle Veridia, and Pinnacle Quant. It is a **risk filter, not a prediction** — a high score means the environment is unfavorable for a signal to succeed, not that the stock will definitely fall.

### Scoring table (revised July 30, 2026 -- see Section 3a for why)

| Factor | Source | Points |
|--------|--------|--------|
| Disclosure-based flags (any combination of 9 flag types) | Pinnacle Sentinel | up to +6, capped |
| Quantitative flags (any combination of 3 flag types) | Pinnacle Sentinel | up to +3, capped |
| VaR wide-band flag active | Pinnacle Veridia | +2 |
| Bullish Pinnacle Quant signal firing into risk context | Pinnacle Quant | +1 |

Maximum possible: 6 + 3 + 2 + 1 = **12**.

### 3a. Why the scoring model changed from the original per-flag design

The original approved version of this document (July 26, 2026) defined 7 factors at fixed point values (2 points each for 4 disclosure flags, 1 point for insider selling, 2 for Veridia, 1 for Quant), built around Pinnacle Sentinel's ORIGINAL 5-flag scope.

Since then, Pinnacle Sentinel's real scope grew to 12 flag types (9 disclosure-based, 3 quantitative). Applying the original "N points per flag, summed linearly" design to 12 real flags would let the disclosure category alone exceed the approved 1-12 ceiling (12 flags x 2 points each could reach 18+ before Veridia/Quant are even added).

**Decision**: rather than silently picking a new set of per-flag weights, or letting the ceiling break, flags are grouped into two capped categories -- disclosure-based flags contribute up to +6 as a GROUP (however many of the 9 fire simultaneously), quantitative flags contribute up to +3 as a group (naturally, since there are only 3). This preserves the original approved 1-12 scale exactly, while still reflecting that more simultaneous flags indicate more concern, without linear blow-up. Validated via an interactive mockup before implementation.

### Score labels and signal actions

| Score | Label | What Pinnacle Quant does | What user sees |
|-------|-------|--------------------------|----------------|
| 1–2 | Clean | BUY recorded normally | BUY badge, no risk note |
| 3–4 | Elevated | BUY → WATCH | WATCH badge + "Pinnacle Veridia: elevated VaR" |
| 5–6 | High | BUY → AVOID | AVOID badge + risk context |
| 7–9 | Severe | BUY → AVOID | AVOID badge + full risk breakdown |
| 10–12 | Extreme | BUY → AVOID | AVOID badge + full breakdown + prominent warning |

### Weightage rationale

The point values reflect the relative strength of evidence for each factor based on academic literature, our own backtest findings (D-015, D-016), and causal logic.

**Disclosure-based flags (capped at +6 as a group):** Pinnacle Sentinel's 9 disclosure flags (late filing, auditor change, CFO resignation, material weakness, debt covenant violation, financial restatement, going concern, SEC investigation/subpoena/whistleblower complaint, revenue recognition change) each represent categorical, documentable corporate events with established predictive value in fraud-detection literature (Beneish M-Score, Dechow et al.). The group cap means one flag and five simultaneous flags don't both trivially hit the ceiling.

**Quantitative flags (capped at +3 as a group):** Beneish M-Score, Altman Z-Score, and Sloan accruals ratio -- naturally capped since there are only 3, each contributing 1 point.

**Pinnacle Veridia VaR wide-band (2 points):** The only statistically validated weight in the table. D-016 demonstrated a 1.78x lift (p=0.0000) on 78 walkforward observations. Two points reflects independent empirical confirmation.

**Pinnacle Quant signal direction (1 point):** The weakest individual factor. A bullish signal firing into a risk environment is a soft contrarian warning. One point.

**Honest caveat:** These weights are our best prior — calibrated against known evidence, defensible on causal grounds, but not yet empirically optimized. They will be recalibrated once Pinnacle Sentinel has 90+ days of live flagging data and we can run a regression against actual outcomes. Critically, per Sentinel's own FOUNDER_OPERATING_MANUAL.md Six-Stage Signal Gauntlet, none of Sentinel's flag-derived points are validated the way Pinnacle Veridia's is -- Sentinel's flags are deployed but have not been through walk-forward backtesting, factor-model validation, or forward validation as of this writing.

### Why no suppression

Signals are never silently suppressed. Even at score 12, the prediction is recorded as AVOID with full context. This is essential for:

1. **Honest validation** — suppressed signals can never be graded. We would have no feedback loop.
2. **User transparency** — users see everything Pinnacle Quant sees, including the risk context that caused a downgrade.
3. **Intellectual honesty** — a platform that hides decisions it isn't confident in can never be trusted when it shows ones it is.

---

## 4. User Experience by Persona

### Persona 1: Retail investor (Pinnacle Quant user)

Gets cleaner signals automatically. Does not need to understand the mechanics.

**Before integration:**
```
PYPL — BUY
Signals: rsi_overbought, price_momentum_5d
```

**After integration:**
```
PYPL — WATCH  ⚠️ Risk Score: 4/12
Signals: rsi_overbought, price_momentum_5d
↳ Downgraded: Pinnacle Veridia wide-band VaR active (elevated uncertainty)
↳ Pinnacle Sentinel: no active flags
```

**High risk example:**
```
SMPL — AVOID  🚫 Risk Score: 8/12
Signals: near_52w_low
↳ Pinnacle Sentinel: Late filing (Jul 18) + CFO exit (Jul 15)
↳ Pinnacle Veridia: wide-band VaR active
↳ Historical context: 94.9% miss rate in similar conditions
```

### Persona 2: Short seller (Pinnacle Sentinel user)

Sees Pinnacle Sentinel flags enriched with Pinnacle Veridia VaR context and Pinnacle Quant signal direction.

```
SMPL | Score: 8/12 | SEVERE
Flags: Late filing (Jul 18) · CFO exit (Jul 15)
Pinnacle Veridia: VaR wide-band active — elevated volatility expected
Pinnacle Quant: near_52w_low fired (bullish signal into bearish context — contrarian note)
Outcome tracking: price −14.2% since first flag (30d)
```

### Persona 3: Risk manager (Pinnacle Veridia user)

Sees VaR calibration enriched with Pinnacle Sentinel flag context.

```
SMPL | VaR breach — Jul 18
Realized loss: −3.1% (exceeded 95% VaR of −2.1%)
Pinnacle Sentinel context: Late filing filed Jul 18 — fundamental driver confirmed
Pinnacle Quant: signal downgraded on this day (correct decision in retrospect)
```

---

## 5. Methodology section text (for all products)

> **Composite Risk Score — 1 to 12**
>
> The composite risk score combines three independent signals from across the Pinnacle Platform. It is a risk filter, not a prediction. A high score means the environment is unfavorable for a bullish signal to succeed — not that the stock will definitely fall.
>
> **1–2 (Clean):** No active risk flags from Pinnacle Sentinel or Pinnacle Veridia. Signal fires normally at full conviction.
>
> **3–4 (Elevated):** One risk factor active — typically Pinnacle Veridia's wide-band VaR flag indicating elevated volatility uncertainty. Bullish signals downgraded from BUY to WATCH.
>
> **5–6 (High):** Two risk factors active. Multiple independent systems flagging the same ticker. Bullish signals downgraded to AVOID.
>
> **7–9 (Severe):** Three or more risk factors active simultaneously. Reserved for situations where Pinnacle Sentinel has multiple red flags AND Pinnacle Veridia confirms elevated VaR. Bullish signals recorded as AVOID.
>
> **10–12 (Extreme):** Maximum risk concentration — typically several Pinnacle Sentinel flags plus Pinnacle Veridia wide-band plus a contradictory Pinnacle Quant signal direction. Score of 12 requires every category to hit its cap simultaneously. Extremely rare.
>
> **What we don't claim:** A score of 8 does not mean the stock will fall. It means multiple independent systems are simultaneously flagging elevated risk. Historical evidence (D-015: p=0.0008; D-016: p=0.0000) shows Pinnacle Veridia's component correlates with higher signal miss rates. Pinnacle Sentinel's flag-derived points are a defensible prior, not yet validated the same rigorous way — pending its own before/after backtest. The score is an input to your decision, not a verdict.

---

## 6. Decision log

| Decision | Date | Description |
|----------|------|-------------|
| D-015 | Jun 2026 | Pinnacle Veridia VaR breaches predict Pinnacle Quant signal misses. chi-sq p=0.0008, 1.46x lift, 1,032 rows. |
| D-016 | Jul 2026 | Pinnacle Veridia per-ticker VaR forecast wired into Pinnacle Quant signal engine. BUY→WATCH on wide-band. Walkforward: 94.9% miss rate vs 53.2%, p=0.0000, 1.78x lift. |
| D-017 | Jul 2026 | Composite risk score 1–12 defined. Scoring table agreed. No suppression policy adopted. |
| D-017 (Sentinel, cont'd) | Jul 30, 2026 | Scoring model revised to capped/banded categories (disclosure +6 cap, quantitative +3 cap) to accommodate Pinnacle Sentinel's real 12-flag scope while preserving the approved 1-12 ceiling. Also: consolidated Ansible deployment role built across all three products; shared-content sync architecture (this document's own distribution mechanism) built. |
| D-020 | Pending | Pinnacle Sentinel flag scoring wired into Pinnacle Quant signal engine. Blocked on Pinnacle Sentinel's Six-Stage Signal Gauntlet validation. |
| D-021 | Pending | Earnings beat/miss detector — Finnhub data source, shared by Pinnacle Quant (BUY signal) and Pinnacle Sentinel (red flag). |

**Numbering note (added 2026-07-30):** this document's own D-series and each product's own decisions.md D-series are SEPARATE namespaces that happen to share the same "D-XXX" format -- confirmed colliding at least once already (D-016 meant something different in each), fixed here by jumping this document's own pending items past Sentinel's current highest (D-018) rather than continuing to guess at a safe gap. Genuinely worth a real, permanent fix later (e.g., prefixing this document's own items as PD-XXX) rather than continuing to manually dodge collisions.

---

## 7. Implementation roadmap

### Phase 1 — Already complete
- [x] Pinnacle Veridia → Pinnacle Quant VaR downweighting (D-016)
- [x] Pinnacle Veridia read-only DB access to Pinnacle Quant predictions (veridia_ro user)
- [x] Cross-product correlation page on Pinnacle Veridia (D-015)
- [x] Composite risk score defined (D-017), later revised to capped/banded categories
- [x] Pinnacle Sentinel EDGAR ingestion pipeline -- 12 flag types built (9 disclosure, 3 quantitative), 2 more attempted and honestly disabled

### Phase 2 — Pinnacle Sentinel integration (in progress)
- [ ] Pinnacle Sentinel flag summary file written daily (`flag_summary_latest.json`) -- NOT built yet
- [ ] Pinnacle Quant reads Pinnacle Sentinel flags at scan time -- blocked on the file above, and on Sentinel's Six-Stage Gauntlet validation per D-020
- [ ] Pinnacle Quant My Signals page shows risk context (score + breakdown)
- [ ] Pinnacle Sentinel screener shows Pinnacle Veridia VaR context per ticker
- [x] Pinnacle Sentinel insider-selling-cluster ingestion (Form 4 XML) built and running; cluster-detection logic itself not yet built

### Phase 3 — Earnings signal
- [ ] Finnhub earnings data pipeline (shared infrastructure)
- [ ] Pinnacle Sentinel: earnings miss → red flag
- [ ] Pinnacle Quant: earnings beat → signal candidate (validate first, 100+ events)

### Phase 4 — Unified risk layer
- [ ] Single composite risk score shown consistently across all three products
- [x] Methodology pages updated with scoring table -- done on Pinnacle Sentinel; Quant and Veridia pending
- [ ] Shared account system (optional — evaluate at launch)

---

## 8. API contracts between products

### Pinnacle Veridia → Pinnacle Quant (current)
**File:** `/veridia_data/ticker_var_forecast_latest.json`
**Written:** Daily by Pinnacle Veridia, before 1pm ET
**Read:** By Pinnacle Quant at scan time
**Key fields:** `ticker`, `wide_band` (bool), `var_return` (float), `horizon_days`

### Pinnacle Sentinel → Pinnacle Quant (planned, not yet built)
**File:** `/sentinel_data/flag_summary_latest.json`
**Written:** Daily by Pinnacle Sentinel, before 1pm ET
**Read:** By Pinnacle Quant at scan time
**Key fields:** `ticker`, `active_flags` (list), `confluence_score` (int), `last_flag_date`

### Pinnacle Sentinel → Pinnacle Veridia (planned, not yet built)
**File:** `/sentinel_data/flag_summary_latest.json` (same file)
**Used by Pinnacle Veridia:** As context for VaR breach attribution

---

## 9. Shared content distribution (this document itself)

This document, `FOUNDER_OPERATING_MANUAL.md`, and the Infrastructure page's content are distributed via `pinnacle-infra/shared_content/` and a hash-based sync script triggered by a git post-commit hook -- see `FOUNDER_OPERATING_MANUAL.md` Section 9 for the full mechanism. Edit the canonical copy in `pinnacle-infra`, never a product repo's local copy directly.

---

## 10. Known limitations (updated July 30, 2026)

1. **Pinnacle Sentinel flag summary file not yet built** — Phase 2's actual file-writing step (`flag_summary_latest.json`) doesn't exist yet, even though the underlying 12 flags are built. This is the real remaining blocker for D-020, not EDGAR ingestion (which is done).
2. **Composite score is untested end-to-end** — D-016 (Pinnacle Veridia component) is validated. Pinnacle Sentinel's component is not validated per its own Six-Stage Signal Gauntlet -- real flag data is currently gated from public visibility on Pinnacle Sentinel specifically because of this.
3. **Earnings signal has data quality risk** — point-in-time consensus estimates require paid data source for rigorous backtesting. Prototype with Finnhub, validate forward before claiming edge.
4. **Shared account system not built** — users currently have separate logins per product.
5. **Score weights are hypotheses** — the point values will be recalibrated once Pinnacle Sentinel has 90+ days of live data.
6. **Insider-selling cluster flag**: real Form 4 transaction ingestion is built and running (285,526-filing historical backfill in progress), but the actual cluster-detection logic (flagging multiple distinct insiders selling within 30 days) is not yet built -- ingestion alone doesn't create flag events.

---

*This document should be reviewed alongside `decisions.md`, `strategy.md`, and `TODO.md` in each product repo.*
*Canonical copy lives at `pinnacle-infra/shared_content/PLATFORM_INTEGRATION.md` -- local copies are synced automatically.*
*Next review: when Pinnacle Sentinel's flag summary file (Phase 2) is built, or when the Six-Stage Gauntlet validation completes.*
