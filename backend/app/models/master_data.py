from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Numeric, Time, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Designation(Base):
    __tablename__ = "designations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Shift(Base):
    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    working_hours = Column(Numeric(4, 2), default=8.0)
    required_work_minutes = Column(Integer, default=480)
    grace_minutes = Column(Integer, default=30)
    lunch_duration_minutes = Column(Integer, default=40)
    lunch_start_time = Column(Time, nullable=True)
    lunch_end_time = Column(Time, nullable=True)
    half_day_hours = Column(Numeric(4, 2), default=4.0)
    minimum_half_day_minutes = Column(Integer, default=240)
    present_hours = Column(Numeric(4, 2), default=8.0)
    minimum_present_minutes = Column(Integer, default=480)
    overtime_start_time = Column(Time, nullable=True)
    late_mark_after_minutes = Column(Integer, default=30)
    early_exit_before_minutes = Column(Integer, default=0)
    is_night_shift = Column(Boolean, default=False)
    overtime_allowed = Column(Boolean, default=True)
    max_overtime_minutes = Column(Integer, default=120)
    timezone = Column(String(50), default="Asia/Kolkata")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class BreakPolicy(Base):
    __tablename__ = "break_policies"
    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    paid_break = Column(Boolean, default=False)
    mandatory = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class AttendancePolicy(Base):
    __tablename__ = "attendance_policies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    required_minutes = Column(Integer, default=480)
    minimum_half_day_minutes = Column(Integer, default=120)
    grace_minutes = Column(Integer, default=15)
    late_arrival_policy = Column(String(255), nullable=True)
    early_exit_policy = Column(String(255), nullable=True)
    overtime_policy = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class WorkLocation(Base):
    __tablename__ = "work_locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)
    unit_type = Column(String(20), nullable=False, default="full_day")
    default_balance_hours = Column(Numeric(10, 2), nullable=False, default=0.0)
    requires_approval = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True, index=True)
    holiday_date = Column(Date, nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    description = Column(String(255), nullable=True)
    is_optional = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
