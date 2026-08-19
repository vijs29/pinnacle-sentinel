"""
One-time (idempotent) schema migration: creates the
pinnacle_sentinel_insider_transactions table using the real SQLAlchemy
model's own schema -- guarantees the created table exactly matches
what the app's ORM expects, rather than a hand-written CREATE TABLE
that could drift.

Uses admin_engine specifically (not the regular restricted app-role
engine) -- creating a table is a DDL/schema operation, which the
restricted pinnacle_sentinel_app role (INF-010 Phase 3) likely can't
perform. Regular INSERT/SELECT/UPDATE (used by form4_ingest.py and
this same session's cluster detector) correctly use the restricted
engine instead.

checkfirst=True makes this safe to run multiple times -- does nothing
if the table already exists.
"""
from app.db.session import admin_engine
from app.models.insider_transaction import InsiderTransaction
from app.models.filing import Filing  # noqa: F401 -- must be imported so
# the FK target (pinnacle_sentinel_filings) is registered in metadata
# before we create a table that references it

InsiderTransaction.__table__.create(bind=admin_engine, checkfirst=True)
print("insider_transactions table creation: done (or already existed)")
