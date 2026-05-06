from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
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
    
    status = Column(String(20), default="Active") # Active, Inactive
    timeoff_balance_hours = Column(Float, default=80.0)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
