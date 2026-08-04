from sqlalchemy import Column, String, DateTime, Boolean
from datetime import datetime
import uuid
from app.db.base import Base


class User(Base):
    __tablename__ = "platform_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
