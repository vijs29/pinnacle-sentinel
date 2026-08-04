# Pinnacle Platform — Founder's Operating Manual
## Pinnacle Sentinel Edition

**Author:** Vijay / RAQA Consultancy LLC
**Version:** 1.0 — August 2026
**Status:** Living document — updated as processes evolve
**Product:** Pinnacle Sentinel — SEC filing red-flag detector

---

## What this document is

The single source of truth for how Pinnacle Sentinel is built, deployed, and operated.
Sections 1-7 are platform-wide rules shared across all Pinnacle products.
Sections 8-9 are Sentinel-specific.

---

## 1. The Core Principle

**Verify, don't assert. Show losses as prominently as wins. Never manufacture evidence.**

Pinnacle Sentinel detects red flags in SEC filings. A red flag that doesn't predict
anything is a disclosed null result, not a hidden failure. The same honesty ethos
that runs through Pinnacle Quant and Pinnacle Veridia applies here.

No flag goes LIVE without passing all six stages of the Signal Gauntlet. There are
no exceptions.

---

## 2. The Six-Stage Signal Gauntlet

No flag type is called "validated" until it passes all six stages:

1. **Hypothesis registration** — falsifiable, written in decisions.md before any data is looked at
2. **Walk-forward backtest** — 500+ spaced samples, excess return >0 at p<0.05, regime-split
3. **Factor model validation** — Fama-French alpha stripping (flag predicts beyond market/size/value)
4. **Forward validation** — 100+ graded live flag events (T+30/90/180/365 vs SPY)
5. **Automated daily audit** — 0 errors/warnings, 20 consecutive trading days
6. **Honest track record publication** — full history including non-predictive flags

**Current status (2026-08-04):** None of Sentinel's 12 built flags have passed the gauntlet.
Flag data is gated behind Vijay's account until at least Stage 4 is reached.

---

## 3. Documentation Rules

- `docs/decisions.md` — every architectural decision, append-only, newest first
- `docs/journal.md` — running work log, oldest first (Sentinel convention)
- `docs/strategy.md` — thesis and why it can win, additive revisions only
- `docs/TODO.md` — living task list, reflects real state
- `docs/FOUNDER_OPERATING_MANUAL.md` — this document
- Journal always delivered as complete file, never an append fragment
- Never fabricate numbers — only use real outputs from actual runs

---

## 4. Build Discipline

- No signal goes LIVE without the Six-Stage Gauntlet
- No flag type is "built" unless detector correctly extracts data from real filings
- All DB writes append-only — no UPDATE on historical flag data
- `create_all(checkfirst=True)` — never drop and recreate tables
- Python 3.12.13 only — consistent across all products

---

## 5. Cross-Product Integration Rules

**Sentinel → Quant (planned, D-018):**
Sentinel writes daily flag summary per ticker. Quant reads at 1pm ET scan time.
Active Sentinel flags downgrade Quant's conviction score.
Not live until at least one flag type passes Stage 4 of the gauntlet.

**Shared DB (D-020):**
All Sentinel tables in `pinnacle_platform` with `pinnacle_sentinel_` prefix.
- `pinnacle_sentinel_filings` (365,387+ rows)
- `pinnacle_sentinel_financial_facts` (851,731+ rows)
- `pinnacle_sentinel_flag_events` (2,746+ rows)
- `pinnacle_sentinel_quant_scores`
- `pinnacle_sentinel_outcomes`
- `pinnacle_sentinel_watchlist_items`
- `pinnacle_sentinel_insider_transactions`
- `platform_users` (shared auth across all products)

---

## 6. Claude Session Management

- No territorial fiefdoms — any Claude session can work on any product
- Verify all facts from handoff prompts before acting on them
- Each session starts with session_audit.py (when built)
- Journal every session before closing

---

## 7. Secrets and Security Rules

- All secrets in Ansible Vault (`pinnacle-infra/group_vars/all/vault.yml`)
- Never commit `.env` files, passwords, or API keys
- DB role separation (INF-010): `pinnacle_sentinel_app` role pending (Phase 3)
- Schema migrations use `DATABASE_ADMIN_URL` (superuser)
- Runtime queries use `DATABASE_URL` (restricted app role, when Phase 3 complete)

---

## 8. Product Standards — Pinnacle Sentinel

### Identity
- **Full name:** Pinnacle Sentinel (never bare "Sentinel")
- **Color:** `#d4443f` (red) — wordmark accent
- **Domain:** `sentinel.pinnacletranscore.com`
- **Port:** 8010 (EC2), 8010 (local dev)
- **UI port:** 5180 (local dev, Vite)

### Health endpoint
```
GET /api/health → {"status": "ok", "product": "pinnacle-sentinel"}
```

### Detection engine (current state, 2026-08-04)
**9 disclosure-based flags (built, in production):**
late filing, auditor change, CFO resignation, material weakness,
debt covenant violation, financial restatement, going concern,
SEC investigation/subpoena/whistleblower complaint, revenue recognition change

**3 quantitative flags (built, in production):**
Beneish M-Score, Altman Z-Score, Sloan accruals ratio

**2 flags attempted, honestly disabled:**
related-party transactions (D-014), say-on-pay vote failure (D-015)

**1 flag in progress:**
Accelerated insider selling — ingestion built, cluster-detection logic pending

**None have passed the Six-Stage Gauntlet.**

### Data (as of 2026-08-04)
- 365,387+ filings ingested
- 851,731+ financial facts
- 2,746 flag events detected
- 503-company S&P 500 universe

---

## 9. Ansible Deployment

All deploys via Ansible only (INF-007). No manual docker compose commands.

```bash
# Standard Sentinel deploy
cd /Users/vijnewmac/projects/PINNACLE/pinnacle-infra
ansible-playbook playbooks/deploy.yml \
  --vault-password-file .vault_pass \
  --tags sentinel

# Dry run first
ansible-playbook playbooks/deploy.yml \
  --tags sentinel --check --diff \
  --vault-password-file .vault_pass
```

### EC2 container
- Container: `pinnacle-sentinel-sentinel-app-1`
- Network: `pinnacle_default`
- DB: `pinnacle_platform` via `DATABASE_URL` from vault

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Aug 2026 | Initial manual. D-020 complete: pinnacle_platform DB, pinnacle_sentinel_* table prefixes, /api/health platform standard, Python 3.12.13 standardized. |
