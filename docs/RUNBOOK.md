# Pinnacle Sentinel — Session Runbook

## Every session starts with this (Mac)

```bash
# From pinnacle-infra terminal — starts all 9 tabs
cd /Users/vijnewmac/projects/PINNACLE/pinnacle-infra
bash scripts/startup.sh
```

Or manually:
```bash
cd /Users/vijnewmac/projects/PINNACLE/pinnacle-sentinel
source .venv-sentinel/bin/activate
```

## Terminal map (after startup.sh)

| Tab | Venv | Purpose |
|-----|------|---------|
| `[.venv-sentinel] Sentinel API :8010` | .venv-sentinel | uvicorn --reload |
| `[Vite] Sentinel UI :5180` | none | npm run dev |
| `[.venv-sentinel] Sentinel Commands` | .venv-sentinel | git, scripts, ingestion |
| Infra terminal | .venv-infra | Ansible deploys, platform tools |

## Rules of the road

1. **Ansible only for EC2 deploys** (INF-007) — no manual docker compose
2. No flag goes LIVE without the Six-Stage Signal Gauntlet
3. Flag data gated behind isVijay until Stage 4 reached
4. All DB writes append-only — never UPDATE historical flag data
5. `.env` files never committed

## Standard Ansible deploy

```bash
cd /Users/vijnewmac/projects/PINNACLE/pinnacle-infra

# Dry run first
ansible-playbook playbooks/deploy.yml --tags sentinel \
  --check --diff --vault-password-file .vault_pass

# Deploy
ansible-playbook playbooks/deploy.yml --tags sentinel \
  --vault-password-file .vault_pass

# Verify
curl -s https://sentinel.pinnacletranscore.com/api/health
```

## EC2 connection

```bash
ssh -i ~/.ssh/pinnacle-quant-ed25519-20260702 ubuntu@52.52.131.132
```

## Scheduled jobs (EC2, APScheduler inside container)

| Schedule | Job | Notes |
|----------|-----|-------|
| TBD | EDGAR ingestion | 503 companies, 4 form types |
| TBD | Outcome grader | T+30/90/180/365 vs SPY |

## Key endpoints

| Endpoint | Purpose |
|----------|---------|
| `/api/health` | Platform health check |
| `/api/screener` | Flag screener |
| `/api/flags` | Flag events |
| `/api/scheduler/status` | APScheduler job status |

## DB tables (pinnacle_platform)

```
pinnacle_sentinel_filings          (365,387+ rows)
pinnacle_sentinel_financial_facts  (851,731+ rows)
pinnacle_sentinel_flag_events      (2,746+ rows)
pinnacle_sentinel_quant_scores
pinnacle_sentinel_outcomes
pinnacle_sentinel_watchlist_items
pinnacle_sentinel_insider_transactions
```

## Check DB on EC2

```bash
ssh -i ~/.ssh/pinnacle-quant-ed25519-20260702 ubuntu@52.52.131.132
docker exec pinnacle-db-1 psql -U pinnacle -d pinnacle_platform -c \
  "SELECT COUNT(*) FROM pinnacle_sentinel_filings;
   SELECT COUNT(*) FROM pinnacle_sentinel_flag_events;"
```

## Session close checklist

1. Commit all changes with descriptive message
2. Update `docs/journal.md` — oldest first (Sentinel convention)
3. Push to GitHub
4. Deploy via Ansible if any backend changes
5. Verify: `curl -s https://sentinel.pinnacletranscore.com/api/health`
