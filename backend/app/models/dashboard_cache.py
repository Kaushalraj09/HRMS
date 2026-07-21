from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.sql import func
from app.core.database import Base

class DashboardCache(Base):
    __tablename__ = "dashboard_caches"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, index=True, nullable=False)
    cached_data = Column(Text, nullable=False) # JSON encoded data
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
