from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Filing(Base):
    __tablename__ = "pinnacle_sentinel_filings"

    id = Column(Integer, primary_key=True)
    cik = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    ticker = Column(String, nullable=True, index=True)
    form_type = Column(String, nullable=False)  # "4", "8-K", "NT 10-K", "NT 10-Q", "10-K", "10-Q"
    accession_number = Column(String, unique=True, nullable=False, index=True)
    filing_date = Column(Date, nullable=False, index=True)
    period_of_report = Column(Date, nullable=True)
    filing_url = Column(String, nullable=False)
    raw_data = Column(JSON, nullable=True)  # parsed XML/text payload, kept for re-processing
    processed = Column(Boolean, default=False)  # has flag detection run on this filing
    ingested_at = Column(DateTime, default=datetime.utcnow)

    flag_events = relationship("FlagEvent", back_populates="filing")


class FlagEvent(Base):
    __tablename__ = "pinnacle_sentinel_flag_events"

    id = Column(Integer, primary_key=True)
    filing_id = Column(Integer, ForeignKey("pinnacle_sentinel_filings.id"), nullable=True)
    quant_score_id = Column(Integer, ForeignKey("pinnacle_sentinel_quant_scores.id"), nullable=True)
    source_type = Column(String, nullable=False, default="disclosure")
    # "disclosure" -- traces to a Filing (late_filing, auditor_change, etc.)
    # "quantitative" -- traces to a QuantScore (sloan_ratio, beneish_m_score, altman_z_score)
    cik = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=True, index=True)
    flag_type = Column(String, nullable=False)
    # disclosure: "late_filing", "auditor_change", "cfo_resignation",
    #             "accelerated_insider_selling", "material_weakness"
    # quantitative: "sloan_ratio_high", "beneish_manipulation_risk", "altman_distress"
    flag_tier = Column(Integer, default=1)
    filing_date = Column(Date, nullable=False)  # T=0; for quantitative flags, fiscal year-end date
    price_at_filing = Column(Float, nullable=True)  # filled in by outcome checker
    details = Column(JSON, nullable=True)  # e.g. {"old_auditor": "X", "new_auditor": "Y"} or score components
    detected_at = Column(DateTime, default=datetime.utcnow)

    filing = relationship("Filing", back_populates="flag_events")
    outcomes = relationship("SentinelOutcome", back_populates="flag_event")


class SentinelOutcome(Base):
    __tablename__ = "pinnacle_sentinel_outcomes"

    id = Column(Integer, primary_key=True)
    flag_event_id = Column(Integer, ForeignKey("pinnacle_sentinel_flag_events.id"), nullable=False)
    horizon_days = Column(Integer, nullable=False)  # 30, 90, 180, 365
    price_at_horizon = Column(Float, nullable=True)
    spy_return_pct = Column(Float, nullable=True)
    stock_return_pct = Column(Float, nullable=True)
    excess_return_pct = Column(Float, nullable=True)  # stock_return - spy_return
    decline_10pct = Column(Boolean, nullable=True)
    decline_20pct = Column(Boolean, nullable=True)
    bankruptcy_or_delisted = Column(Boolean, default=False)
    graded_at = Column(DateTime, nullable=True)  # null until graded

    flag_event = relationship("FlagEvent", back_populates="outcomes")


class WatchlistItem(Base):
    __tablename__ = "pinnacle_sentinel_watchlist_items"

    id = Column(Integer, primary_key=True)
    cik = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=True)
    company_name = Column(String, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)
    is_personal_experiment = Column(Boolean, default=False)
