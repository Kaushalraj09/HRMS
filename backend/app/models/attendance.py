from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Time, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False, server_default=func.current_date())
    
    scheduled_start = Column(Time, nullable=True)
    scheduled_end = Column(Time, nullable=True)
    task_description = Column(String(255), nullable=True)
    
    check_in = Column(Time)
    check_out = Column(Time)
    
    break_minutes = Column(Integer, default=0)
    total_working_minutes = Column(Integer, default=0)
    total_worked_seconds = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    grand_total_minutes = Column(Integer, default=0)
    
    work_mode = Column(String(20), default="Office") # Office, Remote
    status = Column(String(50), default="Not Marked") # Present, Late, Half-Day, Leave, Absent, Not Marked
    is_working = Column(Integer, default=0) # 0 = Not Working, 1 = Working
    
    # Location tracking
    check_in_latitude = Column(Float, nullable=True)
    check_in_longitude = Column(Float, nullable=True)
    check_in_address = Column(String(500), nullable=True)
    check_out_latitude = Column(Float, nullable=True)
    check_out_longitude = Column(Float, nullable=True)
    check_out_address = Column(String(500), nullable=True)
    
    # Image tracking
    check_in_image = Column(String, nullable=True)
    check_out_image = Column(String, nullable=True)
    
    # Relationships
    employee = relationship("Employee", backref="attendance_records")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def punch_in_time(self):
        return self.check_in

    @property
    def punch_out_time(self):
        return self.check_out


class PunchLog(Base):
    __tablename__ = "punch_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=True)
    date = Column(Date, nullable=False, server_default=func.current_date())
    
    punch_in = Column(DateTime(timezone=True))
    punch_out = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer, default=0)
    work_mode = Column(String(20), default="Office")
    
    # Location tracking
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)
    
    # Image tracking
    image = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DailySummary(Base):
    __tablename__ = "daily_summary"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_daily_summary_employee_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False, server_default=func.current_date())
    total_worked_hours = Column(Float, default=0.0, nullable=False)
    overtime = Column(Integer, default=0, nullable=False)
    late_minutes = Column(Integer, default=0, nullable=False)
    early_leave = Column(Integer, default=0, nullable=False)

    employee = relationship("Employee", backref="daily_summaries")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
