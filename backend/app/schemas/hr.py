from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

class HrCreate(BaseModel):
    fullName: str
    email: EmailStr
    phone: str
    department: str
    designation: str
    temporaryPassword: str
    status: str = "Active"

class HrResponse(BaseModel):
    id: int
    hrCode: str
    fullName: str
    email: str
    department: str
    designation: str
    status: str
    createdAt: datetime

    class Config:
        from_attributes = True
