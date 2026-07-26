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
    """Return recent detected flags (FlagEvent, LEFT JOINed with Filing),
    not raw unflagged filings. FIXED 2026-07-25: old flat-schema references
    (would 500). FIXED 2026-07-27: was an INNER JOIN on Filing, which
    silently excluded every quantitative flag (source_type='quantitative',
    filing_id=NULL, e.g. Beneish/Altman/Sloan flags -- see decisions.md
    D-011) from ever appearing here. Now LEFT JOIN, with company_name
    resolved from any Filing row sharing the same CIK when the flag has
    no Filing of its own."""
    from app.db.session import SessionLocal
    from app.models.filing import Filing, FlagEvent
    db = SessionLocal()
    try:
        q = (
            db.query(FlagEvent, Filing)
            .outerjoin(Filing, FlagEvent.filing_id == Filing.id)
        )
        if flag_type:
            q = q.filter(FlagEvent.flag_type == flag_type)
        rows = q.order_by(FlagEvent.filing_date.desc()).limit(limit).all()

        name_cache = {}
        def _company_name_for_cik(cik):
            if cik in name_cache:
                return name_cache[cik]
            row = db.query(Filing.company_name).filter(Filing.cik == cik).first()
            name = row[0] if row else None
            name_cache[cik] = name
            return name

        results = []
        for flag, filing in rows:
            if filing is not None:
                company_name = filing.company_name
                form_type = filing.form_type
                filing_url = filing.filing_url
            else:
                company_name = _company_name_for_cik(flag.cik)
                form_type = (flag.details or {}).get("score_type")
                filing_url = None

            results.append({
                "id":           flag.id,
                "ticker":       flag.ticker,
                "company_name": company_name,
                "form_type":    form_type,
                "filing_date":  flag.filing_date.isoformat() if flag.filing_date else None,
                "flag_type":    flag.flag_type,
                "flag_tier":    flag.flag_tier,
                "source_type":  flag.source_type,
                "details":      flag.details,
                "filing_url":   filing_url,
            })
        return results
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
