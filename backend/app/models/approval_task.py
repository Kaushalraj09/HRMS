from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(30), nullable=False) # timeoff, regularization
    request_id = Column(Integer, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assigned_role = Column(String(20), nullable=False, default="hr")
    status = Column(String(20), nullable=False, default="pending") # pending, approved, rejected, cancelled
    priority = Column(String(20), nullable=False, default="normal")
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    decision_comment = Column(String(500), nullable=True)

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], backref="approval_tasks")
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
