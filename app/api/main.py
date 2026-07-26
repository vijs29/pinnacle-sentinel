from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router

app = FastAPI(title="Pinnacle Sentinel API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/")
def root():
    return {"status": "ok", "product": "Pinnacle Sentinel"}

@app.get("/api/health")
def health():
    return {"status": "healthy"}

@app.get("/api/filings")
def get_filings(
    flag_type: str = None,
    limit: int = 50,
):
    """Return recent detected flags (FlagEvent joined with Filing), not raw
    unflagged filings. FIXED 2026-07-25: this endpoint previously referenced
    the OLD flat pre-redesign schema (Filing.confluence_score, Filing.flag_type,
    etc.) which no longer exist -- would 500 on every call. Now queries the
    real normalized schema (Filing + FlagEvent, see decisions.md D-007)."""
    from app.db.session import SessionLocal
    from app.models.filing import Filing, FlagEvent
    db = SessionLocal()
    try:
        q = (
            db.query(FlagEvent, Filing)
            .join(Filing, FlagEvent.filing_id == Filing.id)
        )
        if flag_type:
            q = q.filter(FlagEvent.flag_type == flag_type)
        rows = q.order_by(FlagEvent.filing_date.desc()).limit(limit).all()
        return [{
            "id":           flag.id,
            "ticker":       flag.ticker,
            "company_name": filing.company_name,
            "form_type":    filing.form_type,
            "filing_date":  flag.filing_date.isoformat() if flag.filing_date else None,
            "flag_type":    flag.flag_type,
            "flag_tier":    flag.flag_tier,
            "details":      flag.details,
            "filing_url":   filing.filing_url,
        } for flag, filing in rows]
    finally:
        db.close()


@app.get("/api/flags/summary")
def get_flags_summary():
    """Counts per flag_type, for the Landing page and Screener filters."""
    from app.db.session import SessionLocal
    from app.models.filing import FlagEvent
    from sqlalchemy import func
    db = SessionLocal()
    try:
        rows = (
            db.query(FlagEvent.flag_type, func.count(FlagEvent.id))
            .group_by(FlagEvent.flag_type)
            .all()
        )
        return {"counts": {flag_type: count for flag_type, count in rows},
                "total": sum(count for _, count in rows)}
    finally:
        db.close()
