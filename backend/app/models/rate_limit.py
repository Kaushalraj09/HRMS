from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.sql import func
from app.core.database import Base


class RateLimitRecord(Base):
    __tablename__ = "rate_limit_records"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_rate_limit_key_locked", "key", "locked_until"),
    )
