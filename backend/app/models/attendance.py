from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False, server_default=func.current_date())
    
    check_in = Column(Time)
    check_out = Column(Time)
    
    break_minutes = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    
    work_mode = Column(String(20), default="Office") # Office, Remote
    status = Column(String(50), default="Not Marked") # Present, Checked In, Checked Out, Absent, Not Marked
    
    # Relationships
    employee = relationship("Employee", backref="attendance_records")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
