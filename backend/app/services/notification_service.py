from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime
from app.models.notification import Notification
from app.core.websocket_manager import manager

async def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    message: str,
    reference_id: Optional[int] = None
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        reference_id=reference_id,
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Push in real-time over WebSocket manager
    try:
        await manager.send_personal_message(
            {
                "type": "NEW_NOTIFICATION",
                "notification": {
                    "id": notification.id,
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "reference_id": notification.reference_id,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat() if notification.created_at else None
                }
            },
            user_id
        )
    except Exception as e:
        print(f"Error sending websocket notification: {e}")

    return notification

def get_user_notifications(db: Session, user_id: int, limit: int = 50) -> List[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )

def get_unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .count()
    )

def mark_notification_read(db: Session, user_id: int, notification_id: int) -> Optional[Notification]:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if notification:
        notification.is_read = True
        notification.read_at = func.now()
        db.commit()
        db.refresh(notification)
    return notification
