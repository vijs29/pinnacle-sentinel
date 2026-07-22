# Pinnacle Sentinel — Handoff Document

Last updated: 2026-07-21. Read this first if picking up a new session —
JOURNAL.md doesn't exist yet for this project (see "Known gaps" below).

## What Sentinel is

SEC filings monitoring product for short-seller / retail red-flag detection.
Detects 5 Tier-1 structured red flags in SEC filings, scores them via a
confluence model (1 flag = WATCH, 2+ = ALERT), and will eventually validate
flags against actual price outcomes (T+30/90/180/365 vs SPY) the same way
Pinnacle Quant validates its trading signals.

Full product rationale, architecture, and v1 scope decisions are in the
conversation history (search past chats for "Pinnacle Sentinel" if picking
this up fresh) — not yet written into a committed docs/ file. **This is the
single biggest gap for a future session to close: there is no
docs/decisions.md or docs/strategy.md for Sentinel, unlike every other
Pinnacle project.**

## Stack & locations

- Repo: shared `PINNACLE` parent git repo on the Mac (NOT its own repo yet —
  `git rev-parse --show-toplevel` returns the PINNACLE parent, and Sentinel
  has zero of its own commits). This should probably be fixed (own repo, per
  the original plan of `github.com/vijs29/pinnacle-sentinel`) before much
  more work goes in — right now nothing is version-controlled.
- Path: `/Users/vijnewmac/projects/PINNACLE/pinnacle-sentinel`
- Backend: FastAPI, port 8010, `.venv` at project root
- Frontend: React/Vite, port 5180 (set explicitly in `ui/vite.config.js`,
  `strictPort: true`)
- DB: Postgres `pinnacle_sentinel`, user `pinnacle`, localhost:5432
- Tables: `filings`, `flag_events`, `sentinel_outcomes`, `watchlist_items`
  (see `app/models/filing.py` for full schema)

## What's built and working

1. **Universe** — S&P 500 constituents + CIK numbers, sourced from Wikipedia
   (`app/services/universe_builder.py`), stored at `app/config/universe.csv`
   (503 rows). NOTE: originally planned to include Russell 1000 via iShares
   IWB holdings CSV — abandoned after confirming Akamai Bot Manager blocks
   scripted access (would require Playwright/headless browser; not worth it
   for a weekly job). Universe is currently S&P 500 only. Not yet scheduled
   to auto-refresh (was deferred until the ingestion scheduler exists —
   still deferred).

2. **EDGAR ingestion** — `app/services/edgar_ingest.py`. Polls SEC's
   submissions API (`data.sec.gov/submissions/CIK##########.json`, NOT
   full-text search — submissions API is the right fit for per-company
   structured polling) for all 503 universe companies, filters to 4 target
   form types (Form 4, 8-K, NT 10-K, NT 10-Q), writes new filings to the
   `filings` table with `processed=False`. Already run once: **342,429
   filings ingested** (full available history per company, not just recent —
   the submissions API's "recent" block returns each company's whole
   history, capped around ~1000 entries). Breakdown: Form 4 285,306 · 8-K
   57,066 · NT 10-Q 32 · NT 10-K 25.

3. **Flag detection — late filing** — `app/services/flag_detector.py`.
   Trivial existence check (NT 10-K/10-Q filing = flag). Run to completion:
   **57 late_filing flags created**, all 57 NT filings processed.

4. **Flag detection — 8-K item codes** — `app/services/flag_detector_8k.py`.
   Fetches each 8-K's actual document, extracts "Item X.XX" sections via
   regex, classifies:
   - Item 4.01 → always `auditor_change`
   - Item 4.02 → `material_weakness` OR `auditor_change`, decided by keyword
     match in the item text (4.02 covers both)
   - Item 5.02 → `cfo_resignation`, ONLY if the item BODY (boilerplate
     heading stripped first) mentions both a CFO role and a
     resignation/departure keyword

   **Real bug found and fixed this session:** naive keyword matching against
   the FULL Item 5.02 text (including its standard boilerplate heading,
   which always contains "departure"/"appointment" regardless of content)
   produced false positives — e.g. flagged 3M's CFO as resigning when the
   filing was actually about RTX's CFO joining 3M's board. Fixed by
   stripping the heading line before keyword matching. Verified against a
   50-filing test batch before/after the fix (5 flags → 2 correct flags).

   **Status: RUNNING IN BACKGROUND as of session end** (PID varies per
   run — check with `ps aux | grep flag_detector_8k`). Launched via:
   `nohup python3 -m app.services.flag_detector_8k 60000 > analysis_8k_output.log 2>&1 &`
   Progress as of last check: **14,050 / 57,066 8-K filings processed
   (~24.6%)**. Results so far: 510 cfo_resignation, 9 auditor_change,
   2 material_weakness. Check progress with:
tail -5 analysis_8k_output.log
psql -h 127.0.0.1 -p 5432 -U pinnacle -d pinnacle_sentinel -c
"SELECT COUNT(*) FROM filings WHERE form_type='8-K' AND processed=true;"
At current pace (~0.2s/request rate limit), expect several more hours to
   complete all 57,066. If the process dies, just re-run the same command —
   it only processes `processed=false` rows, so it's safe to resume.

## What's NOT built yet (in priority order per original v1 plan)

1. **Accelerated insider selling detector** (Form 4 signals, 285,306 filings
   already ingested and waiting). This is the hardest of the 5 flags —
   needs per-insider historical baseline computation (e.g. trailing 90-day
   selling activity), not a single-filing check like the others. Not started.

2. **Confluence scorer** — turns flag_events into WATCH/ALERT classifications
   per company (1 flag = WATCH, 2+ = ALERT). Not started; straightforward
   once insider-selling detection exists (currently only late_filing and
   3 of the 8-K flags would feed it, insider selling is likely the highest-
   value flag for the target audience of short sellers).

3. **Outcome validation loop** — the `sentinel_outcomes` table exists
   (schema built) but nothing populates it yet. Needs: fetch price at
   filing date (T=0) and at T+30/90/180/365, compute excess return vs SPY,
   flag decline_10pct/decline_20pct/bankruptcy_or_delisted. This is the
   Sentinel equivalent of Quant's outcome_checker — same statistical
   rigor should apply (and given today's Quant session, use cluster-robust
   testing / net-of-cost thinking from the start rather than retrofitting).

4. **Pushover notification wiring** — `.env` has empty
   `PUSHOVER_USER_KEY`/`PUSHOVER_APP_TOKEN` placeholders. Reuse Quant's
   dedup pattern once flags are actually alert-worthy (post confluence
   scorer).

5. **Frontend** — `Landing.jsx` and `Screener.jsx` do not exist yet (only
   empty `src/pages/` directory + `App.jsx` importing them, which currently
   causes a Vite error if the frontend dev server is accessed). Deliberately
   deferred multiple times this session in favor of backend/data work.
   `/api/filings` endpoint in `app/api/main.py` also still references the
   OLD single-table schema (`Filing.confluence_score`, `Filing.flag_type`,
   etc.) that predates the current normalized `Filing`/`FlagEvent`/
   `SentinelOutcome` schema — will 500 if called. Needs a full rewrite once
   there's a reason to build the UI against it.

## Known gaps / cleanup items for a future session

- No git repo, no commit history, no docs/decisions.md, docs/strategy.md,
  or JOURNAL.md — unlike every other Pinnacle project. Should be fixed
  before this grows much further; right now a lost Mac = lost Sentinel
  entirely (unlike Quant, which has a full git history and cloud remote).
- `/api/filings` endpoint is broken against the current schema (see above).
- No scheduled/cron jobs exist yet for anything (ingestion, flag detection,
  universe refresh) — everything so far has been manual one-off script runs.
- iShares/Akamai bot-blocking finding should probably be written somewhere
  more permanent than this handoff doc if Russell 1000 coverage is revisited.
