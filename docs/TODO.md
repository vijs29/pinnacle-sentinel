# Pinnacle Sentinel — Master TODO / Path to Real Launch

**Status:** Living document. Reflects real state as of 2026-07-30.
**Purpose:** One place to see everything done, in progress, and remaining
before Sentinel can honestly be called "live" — not just deployed, but
validated per FOUNDER_OPERATING_MANUAL.md's own standard.

---

## 🔴 TOP PRIORITY -- gate flag visibility, decided 2026-07-30

**Decision (Vijay)**: since none of Sentinel's 12 flags have passed the
Six-Stage Signal Gauntlet (see below), real flag data should NOT be
publicly visible right now. Chosen approach: gate it behind Vijay's own
account (same isVijay pattern already used on the Infrastructure page),
not a full public takedown -- Vijay can still see/test the real product,
public visitors see a "not yet validated" placeholder instead.

- [ ] Gate Screener's real flag table behind isVijay check
- [ ] Gate Landing's flag-tape / summary stats behind isVijay check
      (confirm scope: applying to both surfaces that show real flag
      data, not just Screener alone -- flag if this is wrong)
- [ ] Public-facing placeholder copy for both surfaces, honest about
      why ("validation in progress," not a vague "coming soon")

---

## ✅ DONE — Detection engine

- [x] 9 disclosure-based flags built and verified against real filings:
      late filing, auditor change, CFO resignation, material weakness,
      debt covenant violation, financial restatement, going concern,
      SEC investigation/subpoena/whistleblower complaint, revenue
      recognition change
- [x] 3 quantitative flags: Beneish M-Score, Altman Z-Score, Sloan
      accruals ratio
- [x] 2 flags attempted, honestly disabled with documented root cause
      (not counted as built): related-party transactions (D-014),
      say-on-pay vote failure (D-015)
- [x] Confluence scoring live on Screener (1 flag = WATCH, 2+ = ALERT)
- [x] Full EDGAR/XBRL ingestion pipeline, 503-company universe, 851K+
      financial facts

## 🔄 IN PROGRESS — Detection engine

- [ ] **Insider selling cluster** (the last original Tier-1 flag):
  - [x] `insider_transactions` model + Form 4 XML ingestion built and
        verified against real filings (Ameren, 3M)
  - [x] Parallelized ingestion (4x speedup, ~0.28s/filing)
  - [ ] Full 285,526-filing historical backfill — **currently running**
        (~6,000 done as of last check; needs to move to EC2 for
        reliability, see Infrastructure section below)
  - [ ] **Cluster-detection logic itself — NOT built.** Ingestion only
        gets raw transactions into the table; nothing yet queries for
        "multiple distinct insiders selling within 30 days" and creates
        the actual `FlagEvent` rows.

## ❌ NOT STARTED — Detection engine

- [ ] None remaining beyond the above — Category 1 + Category 2 scope
      is otherwise complete (built or honestly disabled)

---

## ⚠️ THE BIG OPEN QUESTION — Six-Stage Signal Gauntlet

Per `FOUNDER_OPERATING_MANUAL.md`: *"No signal goes LIVE without passing
all six stages. There are no exceptions."*

**None of Sentinel's 12 built flags have been through this.** What's
been verified is that each detector correctly *extracts data from real
filings* — not that any flag *predicts* future price behavior.

- [ ] Stage 1 — Hypothesis registration (falsifiable, written down) —
      arguably already implied by strategy.md's thesis, but not
      formalized per-flag
- [ ] Stage 2 — Walk-forward backtest (500+ spaced samples, win rate
      >54% at p<0.05, regime-split) — **not started**
- [ ] Stage 3 — Factor model validation (Fama-French alpha stripping)
      — **not started**
- [ ] Stage 4 — Forward validation (100+ graded live predictions) —
      **not started**. `sentinel_outcomes` table exists; nothing
      populates it. No T+30/90/180/365 price-grading job exists yet.
- [ ] Stage 5 — Automated daily audit (0 errors/warnings, 20
      consecutive trading days) — **not started**, no audit script
      exists
- [ ] Stage 6 — Honest track record publication — **not started**,
      no public track-record page exists

**Decision made (see TOP PRIORITY above)**: real flag data gated behind
Vijay's own account until this gauntlet is complete.

---

## ✅ DONE — Product / UI

- [x] Landing, Screener, Methodology, Watchlist (stub), Login, Register
      pages
- [x] RaqaFooter on all pages
- [x] Methodology page: Platform Integration section (product cards,
      capped/banded composite score 1-12, D-016 stat explained, honest
      caveats), Pinnacle Sentinel divider, prominent 285,526-filing
      stat, naming sweep to full product names
- [x] NavBar: Infrastructure dropdown (hosts Sentinel's own copy of the
      shared Infrastructure page content) + mobile hamburger menu
- [x] Infrastructure page built (copied from Quant, content is genuinely
      shared/common)

## ❌ NOT STARTED — Product / UI

- [ ] **Watchlist real feature** — still just a "coming soon" stub, no
      actual add/remove/notify functionality
- [ ] **Auth system end-to-end test** — register/login/logout/change-
      password all built, never actually tested with a real account
      end-to-end
- [ ] Composite risk score — designed and explained in Methodology
      copy, but **not actually computed or displayed live anywhere** in
      the product (no real badge on Screener showing the 1-12 score)

---

## ✅ DONE — Cross-product integration groundwork

- [x] `PLATFORM_INTEGRATION.md` reviewed; confirmed file-based
      architecture (`/sentinel_data/flag_summary_latest.json`), not a
      database cross-read
- [x] Capped/banded composite-score design (respects the approved 1-12
      ceiling with all 12 real flags) — mocked, validated, written into
      Methodology copy

## ❌ NOT STARTED — Cross-product integration

- [ ] **`flag_summary_latest.json` writer** — the actual file Quant will
      read at scan time. Not built at all.
- [ ] Quant-side reading of that file (not Sentinel's task, but a
      dependency for the integration to mean anything)
- [ ] Cross-product statistical validation (chi-square or equivalent,
      p<0.05) proving Sentinel's flags actually predict anything before
      wiring the connection — blocked on the Six-Stage Gauntlet above

---

## ✅ DONE — Infrastructure / Deployment

- [x] Sentinel deployed to production (`sentinel.pinnacletranscore.com`),
      Docker, Caddy routing, DNS, APScheduler (7 automated jobs)
- [x] Discovered `pinnacle-infra` (existing Ansible automation, not
      built today) — found and fixed a real git-auth gap (D-017)
- [x] Consolidated 3 duplicate product roles into one parameterized
      `pinnacle_product` role, designed to support future products with
      minimal changes
- [x] Fixed a real Veridia-specific bug found via actual dry run
      (wrong compose file assumed)
- [x] **Found and fixed a serious gap**: `pinnacle-infra`'s entire
      working automation (real roles, playbooks, encrypted vault with
      every production secret) had never been committed to git —
      existed only on local disk. Now properly committed and pushed.
- [x] All three products (quant/veridia/sentinel) verified via
      `--check --diff` dry run — clean, zero failures

## ❌ NOT STARTED — Infrastructure / Deployment

- [ ] **Rename Docker Compose services across all three products** to
      `pinnacle-quant` / `pinnacle-veridia` / `pinnacle-sentinel`
      (currently `app` / `veridia-app` / `sentinel-app` -- three
      genuinely different, inconsistent names, confirmed by checking
      each product's real compose file directly rather than assumed).
      Real, cross-product, higher-stakes change: touches Quant's and
      Veridia's live running services, not just Sentinel's. Needs, at
      minimum: renaming the `services:` key in each product's compose
      file, updating each product's Caddyfile `reverse_proxy` directive
      to match, updating `group_vars/all/vars.yml`'s `service_name`
      field per product (added 2026-07-30 for the health-check fix,
      would need updating again), and a full grep of each repo for any
      other reference to the old service name before killing/renaming
      any running container. Deliberately sequenced AFTER Sentinel's
      own in-flight health-check fix and deploy, not folded into the
      same change.
- [x] **Run the consolidated Ansible role for real** against
      production -- DONE 2026-07-30 for Sentinel specifically, after
      finding and fixing 7 real bugs along the way (see decisions.md
      D-018: git auth, Veridia compose file, health-check networking,
      SECRET_KEY naming, stale vault password, build:policy image
      caching, Caddy 28-hour-stale reload). Verified live:
      sentinel.pinnacletranscore.com returns 200, /api/health healthy.
      Today's Methodology/NavBar/Infrastructure UI work is now
      actually deployed for the first time (it was committed all day
      but never really live, due to the build:policy bug).
      NOT yet re-run for Quant or Veridia with these same fixes --
      the shared pinnacle_product/caddy roles apply automatically once
      deployed, but neither has actually been redeployed yet.
- [ ] **Shared-content-via-Ansible architecture** — `pinnacle-infra`
      becoming the single source of truth for
      `FOUNDER_OPERATING_MANUAL.md`, `PLATFORM_INTEGRATION.md`, and the
      Infrastructure page content, templated to each product repo at
      deploy time. Confirmed as the direction; not built.
- [ ] **Move the Form 4 backfill to EC2** — currently running on
      Vijay's Mac; needs: (1) deploy latest code to production first,
      (2) create `insider_transactions` table on production DB, (3)
      migrate the ~6,000+ filings' worth of data already ingested
      locally (dump/restore, same pattern as the original DB
      migration), (4) run the remaining backlog on EC2 via `screen`/
      `tmux` so it survives disconnection
- [ ] `verify_deploy.sh` script — referenced as required in
      `FOUNDER_OPERATING_MANUAL.md`, doesn't exist in Sentinel's repo
- [ ] `session_start.sh` script — same, referenced but doesn't exist
- [ ] Pricing/billing gates — Stripe presumably disabled per Manual's
      launch-gate rules, but this hasn't been explicitly confirmed for
      Sentinel specifically

---

## 🤔 OPEN CONFLICTS — need Vijay's explicit decision, not silently picked

- [ ] **Brand color**: `FOUNDER_OPERATING_MANUAL.md` says Sentinel's
      accent is `#dc2626`. Actual deployed code uses `#d4443f` (Vijay's
      own explicit choice earlier this session). Which is correct going
      forward?
- [ ] **Veridia's accent**: `#0d9488` (Manual) vs `#1d9e75` (used in
      RAQA homepage work) — not Sentinel's to resolve alone, but
      surfaced during this audit
- [ ] **NavBar dropdown standard**: Manual states every product needs
      "Research, Tools, Analysis, Infrastructure" dropdowns — these are
      literally Quant's own dropdown names, generalized into a rule
      that doesn't fit Sentinel's real content. The Manual itself likely
      needs correcting.
- [ ] **`pinnacle-infra` documentation ownership**: should this repo
      have its own `decisions.md`/`journal.md`, rather than having its
      cross-product changes tracked inside Sentinel's docs by
      convention (as has happened with D-017)?

---

## Suggested real order of operations from here

1. ~~Decide the Six-Stage Gauntlet question~~ -- DONE, see TOP PRIORITY
2. Build the flag-visibility gating (in progress now)
3. Move Form 4 backfill to EC2 (reliability, given it's a 20+ hour job)
4. Run the consolidated Ansible role for real (deploys today's UI work)
5. Build the cluster-detection logic once enough Form 4 data exists
6. Build the outcome-grading job (T+30/90/180/365 vs SPY) — the actual
   engine behind Stages 2/4/6 of the Gauntlet
7. Build `flag_summary_latest.json` writer (only meaningful once
   flags are validated, per Gauntlet rules)
8. Resolve the brand-color and NavBar-standard conflicts
9. Build the shared-content-via-Ansible architecture
