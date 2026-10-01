from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Float, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    reporting_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    legacy_employee_code = Column(String(50), nullable=True, index=True)
    
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
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True, index=True)
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

    # Banking & Statutory Info
    bank_name = Column(String(100), nullable=True)
    bank_account_no = Column(String(50), nullable=True)
    ifsc_code = Column(String(30), nullable=True)
    micr_code = Column(String(30), nullable=True)
    pan_number = Column(String(20), nullable=True)
    uan_number = Column(String(30), nullable=True)
    pf_number = Column(String(50), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reporting_manager = relationship("Employee", remote_side=[id], foreign_keys=[reporting_manager_id])
    shift = relationship("Shift", foreign_keys=[shift_id])
    code_history = relationship(
        "EmployeeCodeHistory",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="desc(EmployeeCodeHistory.changed_at)"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def employee_id(self) -> int:
        """Expose internal permanent technical database identity."""
        return self.id

    @property
    def pan(self) -> str | None:
        return self.pan_number

    @property
    def pan_card_number(self) -> str | None:
        return self.pan_number

    @property
    def uan(self) -> str | None:
        return self.uan_number

    @property
    def pf_no(self) -> str | None:
        return self.pf_number

    @property
    def reporting_manager_name(self) -> str | None:
        if not self.reporting_manager:
            return None
        return f"{self.reporting_manager.first_name or ''} {self.reporting_manager.last_name or ''}".strip()

    @property
    def user_role(self) -> str:
        if self.user and self.user.role:
            return self.user.role.name
        return "Employee"

    @property
    def is_manager(self) -> bool:
        if self.user and self.user.role:
            return self.user.role.name.lower() == "manager"
        return False

    @property
    def direct_reports_count(self) -> int:
        if hasattr(self, "_direct_reports_count"):
            return self._direct_reports_count
        return 0

    @direct_reports_count.setter
    def direct_reports_count(self, value: int):
        self._direct_reports_count = value


class EmployeeShift(Base):
    __tablename__ = "employee_shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class EmployeeCodeSequence(Base):
    """Sequence counter for generating zero-padded company employee codes (e.g. AIVAN024)."""
    __tablename__ = "employee_code_sequences"

    id = Column(Integer, primary_key=True, index=True)
    prefix = Column(String(20), unique=True, nullable=False, default="AIVAN", index=True)
    next_number = Column(Integer, nullable=False, default=1)
    padding = Column(Integer, nullable=False, default=3)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class EmployeeCodeHistory(Base):
    """Immutable audit log of all employee code allocations and authorized changes."""
    __tablename__ = "employee_code_history"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    old_employee_code = Column(String(50), nullable=True)
    new_employee_code = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    changed_by = Column(String(150), nullable=False)  # User email or SYSTEM
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employee = relationship("Employee", back_populates="code_history")
