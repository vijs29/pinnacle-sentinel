from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Float, ForeignKey
from datetime import datetime
from app.db.base import Base


class InsiderTransaction(Base):
    """One row per real Form 4 transaction (nonDerivativeTransaction only --
    NOT nonDerivativeHolding, which is an informational balance, not a
    real transaction). Dedicated table rather than Filing.raw_data JSON,
    since cluster detection needs cross-filing, cross-insider aggregation
    queries ("how many distinct insiders sold in the last 30 days") that
    JSON blobs can't do efficiently.

    Verified against a real filing (Ameren/AEE, Warner Baxter, 2017-06-09)
    before building -- confirmed the real XML schema uses transactionCode
    "S" for open-market sales specifically (vs "G" gift, "A" award, etc.,
    which are NOT discretionary sales and should not count toward a
    selling-cluster signal), and rptOwnerCik as the stable per-insider
    identifier (not name matching, which can vary in formatting)."""
    __tablename__ = "pinnacle_sentinel_insider_transactions"

    id = Column(Integer, primary_key=True)
    filing_id = Column(Integer, ForeignKey("pinnacle_sentinel_filings.id"), nullable=False, index=True)

    issuer_cik = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=True, index=True)

    insider_cik = Column(String, nullable=False, index=True)  # rptOwnerCik -- stable ID, not name text
    insider_name = Column(String, nullable=True)
    is_officer = Column(Boolean, default=False)
    is_director = Column(Boolean, default=False)
    is_ten_percent_owner = Column(Boolean, default=False)
    officer_title = Column(String, nullable=True)

    transaction_date = Column(Date, nullable=False, index=True)
    transaction_code = Column(String, nullable=False)  # S=sale, A=award, G=gift, M=exercise, F=tax, etc.
    acquired_disposed_code = Column(String, nullable=True)  # A=acquired, D=disposed
    shares = Column(Float, nullable=True)
    price_per_share = Column(Float, nullable=True)
    shares_owned_after = Column(Float, nullable=True)

    ingested_at = Column(DateTime, default=datetime.utcnow)
