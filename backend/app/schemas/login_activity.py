from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class LoginActivityBase(BaseModel):
    user_id: int
    employee_id: Optional[int] = None
    browser: Optional[str] = None
    device: Optional[str] = None
    operating_system: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    status: str

class LoginActivityCreate(LoginActivityBase):
    pass

class LoginActivityResponse(BaseModel):
    id: int
    user_id: int
    employee_id: Optional[int] = None
    login_time: datetime
    browser: Optional[str] = None
    device: Optional[str] = None
    operating_system: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    status: str
    created_at: datetime
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    user_display_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
