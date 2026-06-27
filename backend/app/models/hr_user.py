from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
class HrUser(Base):
    __tablename__ = "hr_users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    hr_settings = Column(String, nullable=True) # Extension configuration/settings json
    
    # Relationship back to the login account
    user = relationship("User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())