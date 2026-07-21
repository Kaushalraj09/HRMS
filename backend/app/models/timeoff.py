from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Float, Time, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TimeOffRequest(Base):
    __tablename__ = "timeoff_requests"
    __table_args__ = (
        Index("ix_timeoff_employee_date_status", "employee_id", "date", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    leave_type = Column(String(50), nullable=False) # Full-Day, Half-Day, Hourly
    duration_hours = Column(Float, nullable=False, default=0.0) # E.g., 8.0, 4.0, 2.5
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    status = Column(String(20), default="Pending") # Pending, Approved, Rejected, Active, Completed
    reason = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    approval_stage = Column(String(20), nullable=False, default="Manager")
    
    # Relationships
    employee = relationship("Employee", backref="timeoff_requests")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
