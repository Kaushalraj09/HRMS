from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # LOGIN_ACTIVITY, NEWS, ATTENDANCE, LEAVE, SYSTEM
    title = Column(String(150), nullable=False)
    message = Column(String(500), nullable=False)
    reference_id = Column(Integer, nullable=True)  # Points to login_activity.id or news.id etc.
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Enterprise fields
    category = Column(String(50), nullable=True)  # LOGIN, PUNCH_IN, PUNCH_OUT, LEAVE_REQUEST, etc.
    severity = Column(String(20), nullable=True)  # INFO, SUCCESS, WARNING, ERROR
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    receiver_role = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    notification_metadata = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    employee = relationship("Employee", foreign_keys=[employee_id])
    creator = relationship("User", foreign_keys=[created_by])

