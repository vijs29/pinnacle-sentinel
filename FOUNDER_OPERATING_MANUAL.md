# Pinnacle Platform — Founder's Operating Manual

**Author:** Vijay / RAQA Consultancy LLC
**Version:** 1.4 — July 2026
**Status:** Living document — updated as processes evolve

---

## What this document is

This is the operating manual for the Pinnacle Platform. It documents the discipline, process, and standards that govern how we build, validate, deploy, and document everything across Pinnacle Quant, Pinnacle Veridia, and Pinnacle Sentinel.

It is written for three audiences:
1. **New Claude sessions** — so any AI assistant can onboard quickly without repeating context
2. **New human collaborators** — so anyone joining can understand the standards before touching code
3. **The founder** — as a commitment device, making the discipline explicit and auditable

If something is not in this document, it has not been decided — not assumed.

**Canonical source**: this document lives at `pinnacle-infra/shared_content/FOUNDER_OPERATING_MANUAL.md` and is synced to each product repo's root by a git-hook-triggered script (see Section 9). Edit the canonical copy in `pinnacle-infra` — never a product repo's local copy directly, since the next sync will overwrite it.

---

## 1. The Core Principle

**Adversarial honesty.**

Every claim this platform makes must survive an adversary trying to disprove it. We validate before claiming. We show losses as prominently as wins. We never manufacture evidence. We never ship a signal because it "feels right."

This principle applies to:
- Signal validation (backtest before LIVE, forward-validate before claiming edge)
- Documentation (what we write must match what we built)
- User-facing copy (no marketing claims without statistical backing)
- Cross-product integration (backtest the lift before wiring the connection)
- **Infrastructure work** (a "successful" deploy that silently didn't rebuild the image, or a health check that was never actually exercised in dry-run mode, is exactly the kind of thing this principle exists to catch — see Section 9's real incident history)

If a signal doesn't work, we say so. If a decision was wrong, we document the correction. A platform that hides its failures can never be trusted when it claims success.

---

## 2. The Six-Stage Signal Gauntlet

No signal goes LIVE without passing all six stages. There are no exceptions.

### Stage 1 — Hypothesis registration
Write down exactly what the signal predicts, in falsifiable terms, before looking at data.

### Stage 2 — Walk-forward backtest
Run the signal on historical data with strict point-in-time replay — no lookahead bias. Minimum 500 spaced samples, win rate >54% at p<0.05, regime-split required.

### Stage 3 — Factor model validation
Strip out market, size, value, and momentum exposures via Fama-French 4-factor regression. If alpha disappears after factor stripping — reject.

### Stage 4 — Forward validation (live predictions)
Record predictions before outcomes. Minimum 100 graded live predictions, win rate consistent with backtest.

### Stage 5 — Automated daily audit
0 errors, 0 warnings for 20 consecutive trading days before charging users.

### Stage 6 — Honest track record publication
Every prediction published before the outcome is known. Wins and losses shown with equal prominence.

---

## 3. Documentation Rules

### What goes where

| Document | Purpose | When to update |
|----------|---------|----------------|
| `JOURNAL.md` | Chronological session log | Every working session |
| `decisions.md` | D-series decisions (D-001, D-002...) | When a significant technical decision is made |
| `strategy.md` | Product direction and roadmap | When direction changes |
| `TODO.md` | Master task list -- done / in-progress / not-started, open decisions needing an explicit call | Every working session where scope changes; reviewed at session start |
| `PLATFORM_INTEGRATION.md` | Cross-product integration strategy | When integration design changes |
| `FOUNDER_OPERATING_MANUAL.md` | This document | When process changes |
| `HANDOFF_*.md` | Context for new Claude sessions | At end of long sessions or context switches |

### Decision numbering (D-series)
Format: `D-XXX | Date | One-line description | Evidence | Decision`. Real production incidents (not just planned decisions) get documented here too, in full, honest detail — see D-018 in Sentinel's own decisions.md for an example of what a real, messy, multi-hour incident writeup looks like.

---

## 4. Build Discipline

### Terminal rules
1. **First line of every terminal block must be `cd` to the correct directory.**
2. **Never edit files manually.** All changes via scripting.
3. **`py_compile` before every deploy.**
4. **`npm run build` before every frontend commit.**
5. **Before changing a shared resource or file, check first whether the
   content/change already exists there.** Decided 2026-08-01, after
   several real mistakes this same day were traceable to skipping this:
   D-series numbering collisions between this document's own D-series
   and each product's decisions.md (same "D-XXX" format used for two
   different things, confirmed colliding at least once), and a section
   nearly getting duplicated in Infrastructure.jsx. Applies to shared
   docs (this Manual, PLATFORM_INTEGRATION.md), shared config
   (vars.yml, vault.yml), and shared code (any role/template used by
   more than one product) -- grep or view the current state before
   adding anything, every time, not just when something feels risky.

### Never do these things
- Never push to production without running verify_deploy
- Never skip py_compile
- Never manually edit .env on the server (use Ansible Vault)
- Never suppress a signal without recording the prediction (AVOID, not silence)
- Never promote a signal to LIVE without completing all six gauntlet stages
- Never claim an edge without showing the statistical evidence
- **Never trust that a "successful" deploy actually changed anything real** — verify the live endpoint directly, every time, not just the deploy tool's own exit code (see Section 9)
- **Never make a manual/direct production change of any kind — no exceptions, including active incidents.** No direct SSH edits, no direct docker commands, no manual server file edits. Every change goes through a written and run Ansible task, always — even under incident pressure. Decided 2026-08-01 (D-020) after several direct emergency fixes during a real incident (D-018) proved exactly why: untracked, easy to forget, and prone to being silently overwritten by the next real deploy. Read-only diagnostic commands (checking logs/files/status via ansible ad-hoc) remain fine — this is about anything that changes state.

---

## 5. Cross-Product Integration Rules

### Before wiring any cross-product signal
1. Statistical validation first (p < 0.05 required, p < 0.001 preferred)
2. Walkforward backtest
3. Document as a D-series decision
4. Fail-silent implementation
5. No suppression

### Current integrations
- **D-016**: Pinnacle Veridia → Pinnacle Quant. VaR wide-band flag downgrades BUY → WATCH. Evidence: 1.78x lift, p=0.0000 (n=78 walkforward).
- **D-015**: Cross-product correlation page on Pinnacle Veridia. Miss rate 79% with breach vs 53% without (p=0.0008, n=1,032).

---

## 6. Claude Session Management

### Starting a new session
1. Check the journal for what was in progress last session
2. Check `TODO.md` for the current master task list, especially any "top priority" section
3. **If working on infrastructure, check `pinnacle-infra`'s own recent commits and Sentinel's decisions.md for the latest D-018 sub-entries** — deployment automation has a real, evolving incident history that changes what's safe to assume

### Ending a session
1. Commit all pending work
2. Update JOURNAL.md and TODO.md with real current state
3. If context is getting long — write a HANDOFF document

---

## 7. Secrets and Security Rules

### Never do these
- Never commit `.env` files to git
- Never commit API keys, passwords, or secrets to git
- Never share production credentials in chat (not even fetched values — pipe them directly between commands, verify via hash comparison, never print plaintext)

### Secrets management (Ansible Vault, live since 2026-07-30)
- All secrets in `pinnacle-infra/group_vars/all/vault.yml`, AES-256 encrypted
- `.env` files generated per-product from Vault via Jinja2 templates (`roles/pinnacle_product/templates/{product}.env.j2`)
- **Real lesson learned**: before trusting a template, diff-check it against the actual live `.env` on the server. Quant's template was missing 15 real variables (including its own auth key and all trading API keys) that a real dry-run diff caught before any damage was done — see D-018. Never assume a template is complete just because it looks reasonable.
- No manual `.env` editing on the server

---

## 8. Product Standards

### Every product page must have
- NavBar with dropdowns relevant to that product's own features, plus a shared Infrastructure dropdown — NOT a fixed literal list copied from one product
- Mobile hamburger menu (below 768px)
- Methodology page with Platform Integration section at top
- Pinnacle [PRODUCT] divider before product-specific content
- Footer with RAQA Consultancy LLC mark
- Full product name in all user-facing text

### Brand standards
- Shield: navy background `#0f1729`, gold P `#d4af37`
- Pinnacle Quant accent: gold `#d4af37`
- Pinnacle Veridia accent: teal `#0d9488` -- **UNRESOLVED as of 2026-07-30**: `#1d9e75` (green) has also been used in practice. Needs an explicit decision.
- Pinnacle Sentinel accent: red `#dc2626` -- **UNRESOLVED as of 2026-07-30**: `#d4443f` is what's actually deployed. Needs an explicit decision.

### Pricing and launch gates
- **Do not charge users until:** 500 graded live predictions at 54%+ win rate, 12 weeks live, 20 consecutive clean audit days
- Stripe billing is disabled pre-launch

---

## 9. Ansible Deployment Automation

### Why Ansible

Before 2026-07-30, every deploy was manual: SSH into EC2, `git pull`, `docker compose up -d --build`, then manually check the site loaded. This worked but had no audit trail, no dry-run safety net, and no way to catch a bad deploy before it went live. `pinnacle-infra` was scaffolded with the intent to automate this — but as discovered on 2026-07-30, **the automation had been built but never actually run for real, for any product, for the life of the project.** The repo itself had never even been committed to git before that day. Everything below reflects what was learned by actually turning it on.

### What Ansible manages

- **Deployment**: git pull, Docker image rebuild, container restart, health verification — one consolidated role (`pinnacle_product`) handles all three products, parameterized by `group_vars/all/vars.yml`'s `products:` list, rather than three separate near-duplicate roles (the original, pre-2026-07-30 design)
- **Secrets**: Ansible Vault, replacing manual `.env` file editing
- **Reverse proxy**: Caddy's config (the Caddyfile itself) is generated from the same `products:` list — one source of truth for which domains route where
- **Database users**: PostgreSQL cross-product read-only grants (veridia_ro, sentinel_ro)

### The consolidated `pinnacle_product` role

One role, invoked three times from `playbooks/deploy.yml`, each with different variables pulled from `vars.yml`:

```yaml
- role: pinnacle_product
  vars:
    product_name: "{{ (products | selectattr('name', 'equalto', 'sentinel') | first).name }}"
    # ...same pattern for repo, dest_dir, port, compose_file, service_name
  tags: [sentinel]
```

Adding a future product (QuantInfra AI, Biosignal — both added as placeholder entries on 2026-07-30) needs only: a new `products:` list entry, a new `{name}.env.j2` template, and a ~6-line invocation block in `deploy.yml`. The role itself never needs to change. Both new placeholders have `caddy_enabled: false` — deliberately, so they get no Caddy block (and no certificate-issuance attempt) until they're actually deployed and DNS-ready. This flag is the intended mechanism for adding future products without ever touching the Caddyfile template again.

### Real commands

```bash
# ALWAYS dry-run first
ansible-playbook playbooks/deploy.yml --tags <product> --check --diff --vault-password-file .vault_pass

# Then for real
ansible-playbook playbooks/deploy.yml --tags <product> --vault-password-file .vault_pass

# Ad-hoc diagnostic commands (checking files, logs, container state) --
# use ansible's ad-hoc mode, not raw ssh, to keep everything within
# the same auditable tooling:
ansible pinnacle_platform -i inventory/production.yml -m command -a "<command>" --vault-password-file .vault_pass

# Exception: genuinely live, indefinite streaming (docker logs -f while
# making a change) doesn't work well through ansible's ad-hoc mode,
# since it runs a command to completion and returns -- it isn't built
# for open-ended interactive sessions. Direct SSH is the right tool for
# that narrow, specific case.
```

### Real incidents found and fixed (2026-07-30) — the actual first real run

Every one of these was found by actually running the automation for real against production, not by inspection or dry-run alone. Full detail in Sentinel's `decisions.md`, D-017 and D-018.

1. **Unauthenticated git clone**, silently overwriting a manually-configured SSH deploy key on the server → shared vault-stored GitHub token
2. **Veridia's distinct compose file** (`docker-compose.web.yml`, a deliberate safety boundary separating the read-only web service from the ledger-writing cron job) assumed to be the same as the other two products → per-product `compose_file` variable
3. **Health check networking**: checked `http://localhost:{port}` from the EC2 *host*, but the compose files deliberately use `expose:` not `ports:` (confirmed the same pattern in Quant's own compose file too — platform-wide, not product-specific) → check runs inside the container instead. Also: this check had been **silently skipped during every `--check` dry run all day** (Ansible doesn't execute live network checks in check mode by default) → added `check_mode: false` so future dry runs actually exercise it
4. **`SECRET_KEY`/`JWT_SECRET` naming mismatch** — Sentinel's own code reads `SECRET_KEY` specifically; the shared template generated `JWT_SECRET`. Confirmed Sentinel-specific (Quant's own code genuinely expects `JWT_SECRET`) — fixed only Sentinel's template
5. **Stale vault Postgres password** — had never actually matched the live password, since the vault had never been exercised for real. Fixed via a script that fetches the real value and updates the vault directly, verified throughout via SHA-256 hash comparison, plaintext never displayed
6. **`build: policy` silently reusing a 2-day-stale Docker image** on every "successful" deploy (confirmed via the image's real build timestamp, not container creation time, which is misleadingly recent regardless of whether the image itself changed) → `build: always`
7. **Caddy ran 28+ hours without reloading**, serving a stale config even though the Caddyfile on disk was correct → built a real `caddy` role (had been scaffolded empty, never finished) with a proper reload handler
8. **A handler restart race condition** — the `.env` template and git-pull tasks both notify a restart handler that fires at the normal Ansible flush point (end of role/play), which could happen *after* the health check already passed, restarting the container again right before the public verification ran → explicit `meta: flush_handlers` before the health check

### The Quant `.env` near-miss

A routine dry-run diff before Quant's first real deploy revealed its `.env` template was missing 15 real, live variables — including `ANTHROPIC_API_KEY`, its own `SECRET_KEY`, and all 6 Alpaca trading keys. Running the deploy as originally planned would have deleted all of them with no replacement, breaking Quant's Claude API access, its own auth, and all trading functionality. Caught entirely by the dry-run-first discipline (Section 4) — fixed by safely fetching the real values and adding them to the vault before ever running for real.

### The four-domain Caddy incident

The most serious incident of the day: what looked like RAQA's SSL breaking turned out to be four simultaneous, distinct root causes taking down all four live domains (quant, veridia, sentinel, raqa) at once — RAQA's Caddy block being silently dropped (it isn't a containerized "product" in the `vars.yml` sense), Quant's own git repo having a *competing, committed* Caddyfile that overwrote the shared one on every Quant deploy, an unrelated pre-existing stale ACME certificate lock causing an endless retry loop, and RAQA's real static files never being mounted into the Caddy container. Full incident writeup, including the coordination with Quant's own Claude session to pause deploys mid-fix, is in Sentinel's `decisions.md` D-018.

**Real architectural gap surfaced, not yet fixed**: Caddy's *config* is now correctly infra-managed, but its *container definition* still lives inside Quant's own compose file — coupling Caddy's lifecycle to Quant's deploys even though it serves everything. Tracked as a follow-up, not rushed.

### Tooling

`ansible-core` and `ansible-lint` are installed directly in Claude's own sandbox (no Docker/EC2 access there, so this provides static analysis only — syntax, FQCN naming, `changed_when` correctness — not functional/runtime testing). Used for real during today's fixes, catching genuine issues before they shipped, not just guessed at.

### Shared Content Architecture

Some content is genuinely common across all three products and should never exist as independently-drifting copies: this document, `PLATFORM_INTEGRATION.md`, and the Infrastructure page's content.

- **Canonical source**: `pinnacle-infra/shared_content/`
- **Sync mechanism**: a hash-based script (`scripts/sync_shared_content.py`), triggered automatically by a git post-commit hook whenever a canonical file changes, copies the updated file to each product repo's real local path
- **Deliberately not** live runtime API calls (would violate the fail-silent principle in Section 5) or deploy-time-only templating (wouldn't prevent local dev-time drift)
- **Deliberately not** auto-committing in destination repos — the sync writes an uncommitted local change; committing and deploying each product's copy remains a deliberate, human action

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jul 2026 | Initial document |
| 1.3 | Jul 30, 2026 | Added `TODO.md` to documentation rules; described the shared-content-sync architecture |
| 1.4 | Jul 30, 2026 | Rewrote Section 9 comprehensively with the real Ansible deployment history: the consolidated role, 8 real bugs found on the first real run, the Quant `.env` near-miss, and the full four-domain Caddy incident. Added explicit warnings throughout about verifying real outcomes rather than trusting tool exit codes, reflecting the day's actual lessons. |

---

*This document's canonical copy lives at `pinnacle-infra/shared_content/FOUNDER_OPERATING_MANUAL.md`. Local copies in each product repo root are synced automatically -- edit the canonical copy, never a local one.*
