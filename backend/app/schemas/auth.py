from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    activeDashboard: Optional[str] = None

class UserSession(BaseModel):
    id: int
    email: str
    displayName: str
    role: str
    status: str
    accessibleDashboards: list[str]
    activeDashboard: Optional[str] = None
    profileImage: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    accessToken: Optional[str] = None
    tokenType: str = "bearer"
    me: Optional[UserSession] = None
    requiresDashboardSelection: Optional[bool] = None
    availableDashboards: Optional[list[str]] = None
    user: Optional[UserSession] = None

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
    confirmPassword: str

class StandardResponse(BaseModel):
    success: bool
    message: str

class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request payload."""
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """Schema for resetting user password using token."""
    token: str
    newPassword: str
    confirmPassword: str


