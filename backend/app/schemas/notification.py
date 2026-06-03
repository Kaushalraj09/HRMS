from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotificationBase(BaseModel):
    user_id: int
    type: str  # LOGIN_ACTIVITY, ATTENDANCE, LEAVE, SYSTEM
    title: str
    message: str
    reference_id: Optional[int] = None
    is_read: bool = False

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationUnreadCount(BaseModel):
    unread_count: int
