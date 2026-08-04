"""
Stores computed quantitative red-flag scores (Sloan ratio, Beneish
M-Score, Altman Z-Score, etc.) per company per fiscal year. See
decisions.md D-011 -- components stored alongside the final value so
scores are auditable, not just a black-box number.
"""
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base


class QuantScore(Base):
    __tablename__ = "pinnacle_sentinel_quant_scores"

    id = Column(Integer, primary_key=True)
    cik = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=True, index=True)
    fiscal_year = Column(Integer, nullable=False)
    score_type = Column(String, nullable=False, index=True)  # "sloan_ratio", "beneish_m_score", "altman_z_score"
    value = Column(Float, nullable=False)
    components = Column(JSON, nullable=True)  # underlying variables used to compute this score
    computed_at = Column(DateTime(timezone=False), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("cik", "fiscal_year", "score_type", name="uq_quant_score_identity"),
    )
