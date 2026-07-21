from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    reporting_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    
    # Basic Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    gender = Column(String(20))
    dob = Column(Date)
    marital_status = Column(String(50))
    blood_group = Column(String(10))
    
    # Employment Info
    department = Column(String(100))
    designation = Column(String(100))
    employee_type = Column(String(50)) # Full-Time, Contract, etc.
    work_location = Column(String(150))
    shift_type = Column(String(50))
    doj = Column(Date)
    
    # Contact Info
    official_email = Column(String(255), unique=True, nullable=False)
    personal_email = Column(String(255))
    mobile = Column(String(20), nullable=False)
    alternate_mobile = Column(String(20))
    emergency_contact_name = Column(String(150))
    emergency_contact_number = Column(String(20))
    
    status = Column(String(20), default="Active", index=True) # Active, Inactive
    timeoff_balance_hours = Column(Float, default=80.0)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reporting_manager = relationship("Employee", remote_side=[id], foreign_keys=[reporting_manager_id])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def reporting_manager_name(self) -> str | None:
        if not self.reporting_manager:
            return None
        return f"{self.reporting_manager.first_name or ''} {self.reporting_manager.last_name or ''}".strip()

class EmployeeShift(Base):
    __tablename__ = "employee_shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
