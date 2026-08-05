from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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


@app.on_event("startup")
def _startup():
    # Ensure all tables exist. create_all is idempotent -- only creates
    # MISSING tables, never alters/drops existing ones. Every model must
    # be imported here first so SQLAlchemy registers its table on
    # Base.metadata BEFORE create_all runs and before any FK needs to
    # resolve it -- this is exactly the fix for the NoReferencedTableError
    # (flag_events.quant_score_id -> quant_scores) that broke
    # investigation_search.py, going_concern_detector.py, and
    # flag_detector_8k.py separately today (2026-07-27) until each was
    # patched by hand to import QuantScore. Registering every model here,
    # once, at real startup, makes that whole class of bug impossible
    # going forward for any future script that imports app.api.main
    # first (which any script run through the API process does).
    from app.db.base import Base
    from app.db.session import admin_engine
    from app.models import filing, user, financial_fact, quant_score  # noqa: F401
    Base.metadata.create_all(admin_engine, checkfirst=True)

    from app.services.scheduler_service import start_scheduler
    start_scheduler()


@app.get("/api/scheduler")
def scheduler_state():
    from app.services.scheduler_service import scheduler_status
    return scheduler_status()


@app.get("/api/health")
def health():
    return {"status": "ok", "product": "pinnacle-sentinel"}

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
                company_name = _company_name_for_cik(
flag.cik)
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


# --------------------------------------------------------------------------
# Static UI serving (production only -- local dev uses Vite's own dev server
# on :5180 instead, per CORS origin above). Built React app lives in
# ui/dist/ after `npm run build`. Mounted LAST so it never shadows /api/*
# routes -- FastAPI matches routes in registration order, and StaticFiles'
# catch-all would otherwise intercept API calls first.
# ---------------------------------------------------------------------------
_UI_DIST = Path(__file__).resolve().parents[2] / "ui" / "dist"

if _UI_DIST.exists():
    app.mount("/assets", StaticFiles(directory=_UI_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Catch-all for client-side routing (react-router) -- any path
        not matched by an API route above serves index.html, letting the
        React app's own router handle it."""
        requested = _UI_DIST / full_path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(_UI_DIST / "index.html")

@app.get("/api/platform/data-inventory")
def get_data_inventory():
    """Return row counts for all platform tables. Public — no auth required."""
    from app.db.session import SessionLocal
    from sqlalchemy import text

    TABLE_META = {
        "pinnacle_sentinel_filings":         {"product": "sentinel", "purpose": "SEC 8-K filings", "usage": "Red flag detection source"},
        "pinnacle_sentinel_financial_facts":  {"product": "sentinel", "purpose": "XBRL financial facts", "usage": "Beneish M-Score, Altman Z-Score"},
        "pinnacle_sentinel_flag_events":      {"product": "sentinel", "purpose": "Detected red flag events", "usage": "Sentinel screening results"},
        "pinnacle_sentinel_outcomes":         {"product": "sentinel", "purpose": "Flag outcome tracking", "usage": "Validates flag predictive power"},
        "pinnacle_sentinel_quant_scores":     {"product": "sentinel", "purpose": "Quantitative risk scores", "usage": "Beneish + Altman scoring"},
        "pinnacle_sentinel_watchlist_items":  {"product": "sentinel", "purpose": "User watchlist companies", "usage": "Personalized monitoring"},
        "pinnacle_quant_predictions":         {"product": "quant",    "purpose": "Signal predictions", "usage": "Quant signal engine"},
        "pinnacle_quant_miss_analysis":       {"product": "quant",    "purpose": "Miss analysis records", "usage": "Signal validation"},
        "pinnacle_quant_scan_results":        {"product": "quant",    "purpose": "Daily scan results", "usage": "Scanner output"},
        "pinnacle_quant_paper_trades":        {"product": "quant",    "purpose": "Paper trade records", "usage": "Alpaca validation loop"},
        "pinnacle_veridia_var_forecast":      {"product": "veridia",  "purpose": "VaR forecasts", "usage": "Daily risk forecasts"},
        "pinnacle_veridia_breach_log":        {"product": "veridia",  "purpose": "VaR breach events", "usage": "Calibration grading"},
        "platform_quality_checks":            {"product": "platform", "purpose": "Data quality results", "usage": "Platform Intelligence"},
        "platform_cron_log":                  {"product": "platform", "purpose": "Cron job heartbeats", "usage": "Cron status page"},
        "platform_users":                     {"product": "platform", "purpose": "User accounts", "usage": "Auth across all products"},
        "platform_founder_manual":            {"product": "platform", "purpose": "Assembled founder manual", "usage": "Internal reference"},
    }

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT tablename, COALESCE(n_live_tup, 0) as row_count
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)).fetchall()

        tables = []
        by_product = {}
        total_rows = 0

        for row in rows:
            name = row.tablename
            count = int(row.row_count)
            meta = TABLE_META.get(name, {})
            product = meta.get("product", "unknown")
            entry = {
                "table_name": name,
                "row_count":  count,
                "product":    product,
                "purpose":    meta.get("purpose", ""),
                "usage":      meta.get("usage", ""),
            }
            tables.append(entry)
            by_product.setdefault(product, []).append(entry)
            total_rows += count

        return {
            "tables":       tables,
            "by_product":   by_product,
            "total_rows":   total_rows,
            "total_tables": len(tables),
        }
    finally:
        db.close()


@app.get("/api/platform/quality-checks")
def get_quality_checks(authorization: str = Header(None)):
    """Return latest platform quality check results. Auth required."""
    from app.db.session import SessionLocal
    from app.core.security import decode_access_token
    from sqlalchemy import text
    from fastapi.responses import JSONResponse

    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

    db = SessionLocal()
    try:
        last_run = db.execute(text(
            "SELECT MAX(checked_at) FROM platform_quality_checks"
        )).scalar()
        rows = db.execute(text("""
            SELECT check_name, status, detail, value, checked_at, product
            FROM platform_quality_checks
            WHERE checked_at = (SELECT MAX(checked_at) FROM platform_quality_checks)
            ORDER BY product, check_name
        """)).fetchall()
        checks = [
            {
                "check_name": r.check_name,
                "status":     r.status,
                "detail":     r.detail,
                "value":      r.value,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
                "product":    r.product,
            }
            for r in rows
        ]
        return {
            "checks":   checks,
            "last_run": last_run.isoformat() if last_run else None,
        }
    finally:
        db.close()

