from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse, NotificationUnreadCount
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return notification_service.get_user_notifications(db, current_user.id)

@router.get("/unread-count", response_model=NotificationUnreadCount)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    count = notification_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}

@router.put("/{id}/mark-read", response_model=NotificationResponse)
def mark_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated = notification_service.mark_notification_read(db, current_user.id, id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return updated
