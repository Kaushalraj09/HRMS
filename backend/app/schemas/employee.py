from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    gender: Optional[str] = None
    dob: Optional[date] = None
    marital_status: Optional[str] = None
    blood_group: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employee_type: Optional[str] = None
    work_location: Optional[str] = None
    shift_type: Optional[str] = None
    doj: Optional[date] = None
    official_email: EmailStr
    personal_email: Optional[EmailStr] = None
    mobile: str
    alternate_mobile: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    status: str = "Active"

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    marital_status: Optional[str] = None
    blood_group: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employee_type: Optional[str] = None
    work_location: Optional[str] = None
    shift_type: Optional[str] = None
    doj: Optional[date] = None
    official_email: Optional[EmailStr] = None
    personal_email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    alternate_mobile: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    status: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    id: int
    user_id: int
    employee_code: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
