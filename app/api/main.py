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
    min_score: int = 1,
    limit: int = 50,
):
    """Return recent filings with red flags."""
    from app.db.session import SessionLocal
    from app.models.filing import Filing
    db = SessionLocal()
    try:
        q = db.query(Filing).filter(Filing.confluence_score >= min_score)
        if flag_type:
            q = q.filter(Filing.flag_type == flag_type)
        filings = q.order_by(Filing.filing_date.desc()).limit(limit).all()
        return [{
            "id":               f.id,
            "ticker":           f.ticker,
            "company_name":     f.company_name,
            "form_type":        f.form_type,
            "filing_date":      f.filing_date.isoformat() if f.filing_date else None,
            "flag_type":        f.flag_type,
            "flag_detail":      f.flag_detail,
            "confluence_score": f.confluence_score,
            "price_at_filing":  f.price_at_filing,
            "outcome_30d":      f.outcome_30d,
            "outcome_90d":      f.outcome_90d,
            "edgar_url":        f.edgar_url,
        } for f in filings]
    finally:
        db.close()
