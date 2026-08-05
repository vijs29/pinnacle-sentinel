import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv()

# Runtime connection — restricted role (pinnacle_sentinel_app after INF-010 Phase 3)
# Used for all application queries (SELECT, INSERT, UPDATE on sentinel tables only)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://pinnacle:pinnacle@localhost:5432/pinnacle_sentinel")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Admin connection — superuser for schema migrations only (create_all / DDL)
# Falls back to DATABASE_URL in local dev where the split isn't configured
DATABASE_ADMIN_URL = os.getenv("DATABASE_ADMIN_URL", DATABASE_URL)
admin_engine = create_engine(DATABASE_ADMIN_URL)
