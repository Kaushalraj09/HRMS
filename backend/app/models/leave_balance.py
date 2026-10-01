from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Float, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class EmployeeLeaveBalance(Base):
    __tablename__ = "employee_leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_emp_leave_year"),
        Index("ix_emp_leave_year", "employee_id", "year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    
    allocated_days = Column(Float, nullable=False, default=0.0)
    used_days = Column(Float, nullable=False, default=0.0)
    pending_days = Column(Float, nullable=False, default=0.0)
    available_days = Column(Float, nullable=False, default=0.0)
    
    carry_forward_days = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    employee = relationship("Employee", backref="yearly_leave_balances")
    leave_type = relationship("LeaveType")

    @property
    def remaining_days(self) -> float:
        return self.available_days
