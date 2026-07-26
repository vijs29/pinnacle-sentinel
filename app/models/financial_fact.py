"""
Local mirror of one (company, concept, period) row from SEC's XBRL
companyfacts API. See decisions.md D-011.

Duration facts (Revenues, NetIncomeLoss, etc.) have both start_date and
end_date populated. Instant facts (Assets, InventoryNet, etc.) have only
end_date -- start_date is NULL, since a balance sheet figure is a
snapshot, not a period.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base


class FinancialFact(Base):
    __tablename__ = "financial_facts"

    id = Column(Integer, primary_key=True)
    cik = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=True, index=True)
    concept = Column(String, nullable=False, index=True)
    unit = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=False)
    fiscal_year = Column(Integer, nullable=True)
    fiscal_period = Column(String, nullable=True)
    form_type = Column(String, nullable=True)
    value = Column(Float, nullable=False)
    accession_number = Column(String, nullable=True)
    ingested_at = Column(DateTime(timezone=False), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "cik", "concept", "unit", "start_date", "end_date", "form_type",
            name="uq_financial_fact_identity",
        ),
    )
