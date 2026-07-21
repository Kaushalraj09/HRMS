from pydantic import BaseModel, computed_field, model_validator, ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict

class NotificationEmployee(BaseModel):
    id: int
    first_name: str
    last_name: str
    avatar: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        return {
            "id": data.id,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "avatar": data.user.profile_image if (hasattr(data, "user") and data.user) else None
        }

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    model_config = ConfigDict(from_attributes=True)

class NotificationBase(BaseModel):
    user_id: int
    type: str  # LOGIN_ACTIVITY, NEWS, ATTENDANCE, LEAVE, SYSTEM
    title: str
    message: str
    reference_id: Optional[int] = None
    is_read: bool = False
    category: Optional[str] = None
    severity: Optional[str] = None
    employee_id: Optional[int] = None
    created_by: Optional[int] = None
    receiver_role: Optional[str] = None
    notification_metadata: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    created_at: datetime
    read_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    employee: Optional[NotificationEmployee] = None

    model_config = ConfigDict(from_attributes=True)

class NotificationUnreadCount(BaseModel):
    unread_count: int

