from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserSession(BaseModel):
    id: int
    email: str
    displayName: str
    role: str
    status: str

    class Config:
        from_attributes = True # This allows Pydantic to read SQLAlchemy models

class LoginResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    me: UserSession

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
    confirmPassword: str

class StandardResponse(BaseModel):
    success: bool
    message: str

