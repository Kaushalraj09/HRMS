from pydantic import BaseModel, ConfigDict, EmailStr, Field
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
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    userId: int = Field(alias="user_id")
    hrCode: str = Field(alias="hr_code")
    fullName: str = Field(alias="full_name")
    email: str
    phone: str
    department: str
    designation: str
    status: str
    createdAt: datetime = Field(alias="created_at")
