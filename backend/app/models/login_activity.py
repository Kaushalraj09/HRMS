from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class LoginActivity(Base):
    __tablename__ = "login_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    login_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    browser = Column(String(100))
    device = Column(String(100))
    operating_system = Column(String(100))
    ip_address = Column(String(50))
    location = Column(String(255), nullable=True)
    status = Column(String(50), default="Success")  # Success, Failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    employee = relationship("Employee", foreign_keys=[employee_id])
