# Pinnacle Sentinel — Handoff Document

Last updated: 2026-07-23 (evening). Read this first if picking up a new session.

## Quick bridge: what happened to Pinnacle Quant recently

If you're a fresh session picking up either project: Quant had a long,
substantial session on 2026-07-21/22 (cluster-robust signal re-analysis,
Alpaca account rotation, a single-source-of-truth signal classification
refactor across 8 files). That project is fully documented in its own
JOURNAL.md and METHODOLOGY.md (Pinnacle-quant-markers-for-stock-market
repo) -- read those first if working on Quant. Quant is considered done
coding-wise for now; it's waiting on forward paper-trading data to
accumulate and grade. This document is Sentinel-only.

## What Sentinel is

SEC filings monitoring product for short-seller / retail red-flag detection.
Detects 5 Tier-1 structured red flags in SEC filings, scores them via a
confluence model (1 flag = WATCH, 2+ = ALERT), and will eventually validate
flags against actual price outcomes (T+30/90/180/365 vs SPY) the same way
Pinnacle Quant validates its trading signals.

Full product rationale, architecture, and v1 scope decisions are in the
conversation history (search past chats for "Pinnacle Sentinel" if picking
this up fresh) -- not yet written into a committed docs/ file. This is
still the single biggest documentation gap: there is no docs/decisions.md,
docs/strategy.md, or JOURNAL.md for Sentinel, unlike every other Pinnacle
project. (The git-repo gap from the previous version of this doc IS now
fixed -- see below.)

## Stack & locations

- Repo: now a real, standalone git repo -- github.com/vijs29/pinnacle-sentinel
  (fixed 2026-07-22; previously had zero commits and lived inside the shared
  PINNACLE parent repo with nothing version-controlled). .gitignore already
  correctly excludes .venv/, node_modules/, .env, *.log, __pycache__/.
- Path: /Users/vijnewmac/projects/PINNACLE/pinnacle-sentinel
- Backend: FastAPI, port 8010, .venv at project root
- Frontend: React/Vite, port 5180 (set explicitly in ui/vite.config.js,
  strictPort: true)
- DB: Postgres pinnacle_sentinel, user pinnacle, localhost:5432
- Tables: filings, flag_events, sentinel_outcomes, watchlist_items
  (see app/models/filing.py for full schema)

## What's built and working

1. Universe -- S&P 500 constituents + CIK numbers, sourced from Wikipedia
   (app/services/universe_builder.py), stored at app/config/universe.csv
   (503 rows). Russell 1000 via iShares IWB was abandoned -- Akamai Bot
   Manager blocks scripted access (would need Playwright; not worth it for
   a weekly job). S&P 500 only for now. Not scheduled to auto-refresh yet.

2. EDGAR ingestion -- app/services/edgar_ingest.py. Polls SEC's submissions
   API for all 503 universe companies, 4 target form types. Already run
   once: 342,429 filings ingested (Form 4 285,306, 8-K 57,066, NT 10-Q 32,
   NT 10-K 25).

3. Flag detection -- late filing -- app/services/flag_detector.py. Complete:
   57 late_filing flags, all 57 NT filings processed.

4. Flag detection -- 8-K item codes -- app/services/flag_detector_8k.py.
   Classifies Item 4.01 -> auditor_change, Item 4.02 -> material_weakness OR
   auditor_change (keyword-decided), Item 5.02 -> cfo_resignation (keyword-
   decided on the body text with the boilerplate heading stripped first --
   a real false-positive bug was found and fixed on 2026-07-21, see git log).

   2026-07-22/23: this job crashed mid-run and was fixed + restarted. The
   version launched at the end of the 2026-07-21 session hit an unhandled
   ReadTimeout from sec.gov and died silently at 14,750/57,016 filings --
   sat dead the rest of that session with zero recovery, since neither the
   fetch function nor the per-filing processing loop had any exception
   handling. Fixed:
   - fetch_filing_text(): retries up to 3x with exponential backoff
     (1s/2s/4s) on network errors, timeout 15s->20s.
   - run() loop: per-filing try/except so one bad filing (bad HTML,
     transient DB issue, etc.) can never crash the remaining batch --
     rolls back just that filing, leaves processed=False for retry,
     continues.
   - Added terminal-notifier-based progress notifications (with sound)
     every 1,000 filings + a completion notification, so liveness is
     visible without checking the log. Note: plain osascript notifications
     did NOT work reliably on this Mac (Terminal.app doesn't self-register
     with Notification Center for them) -- had to install
     brew install terminal-notifier instead, which registers properly.
     If notifications aren't appearing, check System Settings ->
     Notifications -> terminal-notifier -> Allow Notifications, and that no
     Focus/DND mode is active.

   Status: RUNNING IN BACKGROUND as of this doc's timestamp (PID varies per
   run -- check with ps aux | grep flag_detector_8k). Relaunched via:
   nohup python3 -m app.services.flag_detector_8k 60000 > analysis_8k_output.log 2>&1 &
   Progress as of last check: 17,450 / 57,066 processed (~30.6%). Check with:

   tail -10 analysis_8k_output.log
   psql -h 127.0.0.1 -p 5432 -U pinnacle -d pinnacle_sentinel -c "SELECT COUNT(*) FROM filings WHERE form_type='8-K' AND processed=true;"
   ps aux | grep flag_detector_8k | grep -v grep

   If it's not running when you check (crashed again despite the fixes, or
   the Mac was asleep/restarted), just re-run the same nohup command -- it
   only processes processed=false rows, fully safe to resume, no duplicate
   work.

## What's NOT built yet (in priority order per original v1 plan)

1. Accelerated insider selling detector (Form 4, 285,306 filings already
   ingested). Hardest of the 5 flags -- needs per-insider historical
   baseline (e.g. trailing 90-day selling activity), not a single-filing
   check. Not started. This is the natural next step once the 8-K job
   finishes.
2. Confluence scorer -- flag_events -> WATCH/ALERT per company. Not
   started; straightforward once insider-selling exists.
3. Outcome validation loop -- sentinel_outcomes table exists, nothing
   populates it. Given Quant's 2026-07-21/22 session, use cluster-robust
   testing from the start here, not as a retrofit.
4. Pushover notification wiring -- .env has empty PUSHOVER_USER_KEY /
   PUSHOVER_APP_TOKEN placeholders.
5. Frontend -- Landing.jsx/Screener.jsx don't exist yet (empty src/pages/,
   App.jsx errors if the dev server is accessed). /api/filings in
   app/api/main.py still references the OLD flat pre-redesign schema --
   will 500 if called, needs a rewrite.

## Known gaps / cleanup items for a future session

- No git repo -- FIXED 2026-07-22, now on GitHub.
- /api/filings endpoint still broken against the current schema.
- No scheduled/cron jobs exist yet for anything.
- No docs/decisions.md, docs/strategy.md, or JOURNAL.md -- still the
  biggest remaining gap, worth doing before this grows much further.
- iShares/Akamai bot-blocking finding should get written somewhere more
  permanent than this doc if Russell 1000 coverage is ever revisited.
