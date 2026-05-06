from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(Integer, primary_key=True, index=True)
    timeoff_request_id = Column(Integer, ForeignKey("timeoff_requests.id"), nullable=False)
    action_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    action = Column(String(50), nullable=False) # APPROVED, REJECTED
    comments = Column(Text, nullable=True)
    
    # Relationships
    timeoff_request = relationship("TimeOffRequest", backref="approval_logs")
    user = relationship("User", foreign_keys=[action_by_user_id])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
