from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Time, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True, index=True)
    date = Column(Date, nullable=False, server_default=func.current_date(), index=True)

    scheduled_start = Column(Time, nullable=True)
    scheduled_end = Column(Time, nullable=True)
    task_description = Column(String(255), nullable=True)
    
    punch_in = Column(Time)
    punch_out = Column(Time)
    
    break_minutes = Column(Integer, default=0)
    total_working_minutes = Column(Integer, default=0)
    total_worked_seconds = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    grand_total_minutes = Column(Integer, default=0)
    
    work_mode = Column(String(20), default="Office") # Office, Remote
    status = Column(String(50), default="Not Marked") # Present, Late, Half-Day, Leave, Absent, Not Marked
    is_working = Column(Integer, default=0) # 0 = Not Working, 1 = Working
    
    # Location tracking
    punch_in_latitude = Column(Float, nullable=True)
    punch_in_longitude = Column(Float, nullable=True)
    punch_in_address = Column(String(500), nullable=True)
    punch_out_latitude = Column(Float, nullable=True)
    punch_out_longitude = Column(Float, nullable=True)
    punch_out_address = Column(String(500), nullable=True)
    
    # Image tracking
    punch_in_image = Column(String, nullable=True)
    punch_out_image = Column(String, nullable=True)
    
    # Enterprise Checkout and Overtime fields
    checkout_source = Column(String(20), default="MANUAL") # AUTO, MANUAL
    _flags = Column("flags", String(500), default="") # Comma-separated flags
    requires_regularization = Column(Boolean, default=False)
    overtime_approved = Column(Boolean, default=False)
    overtime_start = Column(Time, nullable=True)
    overtime_end = Column(Time, nullable=True)
    
    # Reminder tracking
    shift_end_reminder_sent = Column(Integer, default=0)
    overtime_reminder_sent = Column(Integer, default=0)
    overtime_extended = Column(Boolean, default=False)

    # Relationships
    employee = relationship("Employee", backref="attendance_records")
    shift = relationship("Shift", foreign_keys=[shift_id])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def punch_in_time(self):
        return self.punch_in

    @property
    def punch_out_time(self):
        return self.punch_out

    @property
    def flags(self) -> list[str]:
        if not self._flags:
            return []
        return [f.strip() for f in self._flags.split(",") if f.strip()]

    @flags.setter
    def flags(self, value):
        if not value:
            self._flags = ""
        elif isinstance(value, list):
            self._flags = ",".join(value)
        else:
            self._flags = str(value)


class AttendanceAuditTrail(Base):
    __tablename__ = "attendance_audit_trail"

    id = Column(Integer, primary_key=True, index=True)
    event = Column(String(50), nullable=False) # e.g. PUNCH_IN, PUNCH_OUT, etc.
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(String(500), nullable=True)

    employee = relationship("Employee", backref="audit_trails")


class AttendanceRegularizationRequest(Base):
    __tablename__ = "attendance_regularization_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    requested_punch_in = Column(Time, nullable=True)
    requested_punch_out = Column(Time, nullable=True)
    reason_type = Column(String(50), nullable=False)
    reason_text = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending") # pending, approved, rejected
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(String(500), nullable=True)
    
    auto_checkout_time = Column(Time, nullable=True)
    requested_time = Column(Time, nullable=True)
    corrected_time = Column(Time, nullable=True)
    manager_decision = Column(String(20), nullable=True)
    hr_decision = Column(String(20), nullable=True)
    audit_status = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    employee = relationship("Employee", backref="regularization_requests")
    reviewer = relationship("User", backref="reviewed_regularizations")

class OvertimeRequest(Base):
    __tablename__ = "overtime_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=True)
    requested_minutes = Column(Integer, nullable=False)
    reason = Column(String(500), nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="Pending") # Pending, Approved, Rejected, Expired, Completed
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    employee = relationship("Employee", backref="overtime_requests")
    reviewer = relationship("User", backref="reviewed_overtimes")





