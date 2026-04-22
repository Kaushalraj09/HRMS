from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
class HrUser(Base):
    __tablename__ = "hr_users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    hr_code = Column(String(30), unique=True, index=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    department = Column(String(100), nullable=False)
    designation = Column(String(100), nullable=False)
    status = Column(String(20), default="Active")
    
    # Relationship back to the login account
    user = relationship("User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())