import re
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, model_validator

COMMON_WEAK_PASSWORDS = {
    "password", "password123", "admin123", "admin@123", "12345678", "123456789",
    "qwerty123", "welcome123", "letmein123", "changeme123", "hrms1234", "root1234"
}

def validate_password_strength(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]/\\~`]", password):
        raise ValueError("Password must contain at least one special character.")
    if password.lower() in COMMON_WEAK_PASSWORDS:
        raise ValueError("Password is too common or easily guessable. Please choose a stronger password.")
    return password


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


class WebSocketTicketResponse(BaseModel):
    ticket: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
    confirmPassword: str

    @field_validator("newPassword")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def verify_passwords_match(self):
        if self.newPassword != self.confirmPassword:
            raise ValueError("New password and confirm password do not match.")
        return self


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

    @field_validator("newPassword")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def verify_passwords_match(self):
        if self.newPassword != self.confirmPassword:
            raise ValueError("New password and confirm password do not match.")
        return self
