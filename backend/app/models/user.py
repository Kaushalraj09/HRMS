from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False) # e.g., 'admin', 'hr', 'employee'

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(150), nullable=False)
    status = Column(String(20), default="Active")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    
    # Relationships
    role = relationship("Role")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
