"""
Pinnacle Sentinel — Session Audit Script
Run at the START of every new session to verify the previous session
was properly closed.
"""
import subprocess, sys, re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RED="\033[91m"; YELLOW="\033[93m"; GREEN="\033[92m"; BOLD="\033[1m"; RESET="\033[0m"

issues=[]; warnings=[]; info=[]

def flag(level, check, msg):
    entry = f"[{level}] {check}: {msg}"
    if level=="ERROR": issues.append(entry); print(f"  {RED}❌ {entry}{RESET}")
    elif level=="WARN": warnings.append(entry); print(f"  {YELLOW}⚠️  {entry}{RESET}")
    else: info.append(entry); print(f"  {GREEN}✓  {entry}{RESET}")

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd or REPO_ROOT)
    return r.stdout.strip()

print(f"\n{BOLD}── Session Audit — Pinnacle Sentinel ──{RESET}")

# Check 0: Correct venv and directory
venv = sys.prefix
repo = str(REPO_ROOT)
if ".venv-sentinel" not in venv:
    flag("ERROR", "Venv", f"Wrong venv active: {venv} — expected .venv-sentinel. Run: source .venv-sentinel/bin/activate")
else:
    flag("INFO", "Venv", f"Correct venv: {venv}")
if "pinnacle-sentinel" not in repo:
    flag("ERROR", "Directory", f"Wrong directory: {repo} — expected pinnacle-sentinel")
else:
    flag("INFO", "Directory", f"Correct directory: {repo}")

# Check 1: Journal currency (Sentinel uses docs/journal.md, oldest first)
journal = None
for candidate in ["docs/journal.md", "docs/JOURNAL.md", "JOURNAL.md"]:
    p = REPO_ROOT / candidate
    if p.exists():
        journal = p
        break

if journal:
    dates = re.findall(r'^## (\d{4}-\d{2}-\d{2})', journal.read_text(), re.MULTILINE)
    if dates:
        last_entry = dates[-1]  # oldest first — last date is newest
        last_commit = run("git log -1 --format=%cd --date=short")
        if last_entry < last_commit:
            flag("WARN", "Journal", f"Last entry {last_entry} behind latest commit {last_commit} — update journal")
        else:
            flag("INFO", "Journal", f"Current — last entry {last_entry}")
    else:
        flag("WARN", "Journal", "No dated entries found")
else:
    flag("ERROR", "Journal", "journal.md not found")

# Check 2: Uncommitted changes
status = run("git status --porcelain")
if status:
    n = len(status.split('\n'))
    flag("WARN", "Git", f"{n} uncommitted change(s) — commit before ending session")
else:
    flag("INFO", "Git", "Working tree clean")

# Check 3: Key docs
for doc in ["docs/decisions.md", "docs/strategy.md", "docs/FOUNDER_OPERATING_MANUAL.md", "docs/journal.md"]:
    p = REPO_ROOT / doc
    if p.exists():
        last = run(f"git log -1 --format=%cd --date=short -- {doc}")
        flag("INFO", doc, f"Last committed: {last}" if last else "never committed")
    else:
        flag("WARN", doc, "Not found")

# Check 4: Production sync
local = run("git rev-parse HEAD")
origin = run("git rev-parse origin/main")
if local != origin:
    flag("WARN", "Sync", f"Local ({local[:8]}) differs from origin/main — push/pull needed")
else:
    flag("INFO", "Sync", f"Matches origin/main ({local[:8]})")

# Check 5: Sentinel-specific — DB tables exist
try:
    import os
    from pathlib import Path
    env_file = REPO_ROOT / ".env"
    db_url = ""
    if env_file.exists():
        for line in env_file.read_text().split('\n'):
            if line.startswith('DATABASE_URL='):
                db_url = line.split('=', 1)[1].strip()
                break
    if db_url:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM pinnacle_sentinel_filings"
            )).scalar()
            flag("INFO", "DB", f"pinnacle_sentinel_filings: {count:,} rows")
    else:
        flag("WARN", "DB", "DATABASE_URL not set in .env — cannot check DB")
except Exception as e:
    flag("WARN", "DB", f"DB check failed: {e}")

print(f"\n  {len(issues)} errors · {len(warnings)} warnings · {len(info)} ok\n")
