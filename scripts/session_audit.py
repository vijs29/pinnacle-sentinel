#!/usr/bin/env python3
"""
Pinnacle Sentinel — Session Audit
Thin wrapper around the platform canonical audit module.
Location: scripts/session_audit.py
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

INFRA_TOOLS = Path(__file__).resolve().parents[2] / "pinnacle-infra" / "tools"
sys.path.insert(0, str(INFRA_TOOLS))

from platform_session_audit import run_audit

load_dotenv()


def db_check():
    """Check DB connectivity and sentinel filing count."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return False, "DATABASE_URL not set in .env — cannot check DB"
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(
                "SELECT COUNT(*) FROM pinnacle_sentinel_filings"
            ))
            count = result.scalar()
        return True, f"pinnacle_sentinel_filings: {count:,} rows"
    except Exception as e:
        return False, f"DB check failed: {e}"


run_audit({
    "product_name":  "Pinnacle Sentinel",
    "expected_venv": ".venv-sentinel",
    "expected_dir":  "pinnacle-sentinel",
    "journal_paths": ["docs/journal.md"],
    "key_docs": [
        "docs/decisions.md",
        "docs/strategy.md",
        "docs/FOUNDER_OPERATING_MANUAL.md",
        "docs/journal.md",
    ],
    "health_url":   "https://sentinel.pinnacletranscore.com/api/health",
    "ledger_check": None,
    "db_check":     db_check,
    "extra_checks": [],
})
