import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime
from sqlalchemy import or_
from app.models.notification import Notification
from app.core.websocket_manager import manager

logger = logging.getLogger(__name__)

async def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    message: str,
    reference_id: Optional[int] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    employee_id: Optional[int] = None,
    created_by: Optional[int] = None,
    receiver_role: Optional[str] = None,
    notification_metadata: Optional[dict] = None
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        reference_id=reference_id,
        is_read=False,
        category=category,
        severity=severity,
        employee_id=employee_id,
        created_by=created_by,
        receiver_role=receiver_role,
        notification_metadata=notification_metadata
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Push in real-time over WebSocket manager
    try:
        employee_dict = None
        if notification.employee:
            avatar = notification.employee.user.profile_image if (notification.employee.user) else None
            employee_dict = {
                "id": notification.employee.id,
                "first_name": notification.employee.first_name,
                "last_name": notification.employee.last_name,
                "full_name": f"{notification.employee.first_name} {notification.employee.last_name}",
                "avatar": avatar
            }

        await manager.send_personal_message(
            {
                "type": "NEW_NOTIFICATION",
                "notification": {
                    "id": notification.id,
                    "user_id": notification.user_id,
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "reference_id": notification.reference_id,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat() if notification.created_at else None,
                    "category": notification.category,
                    "severity": notification.severity,
                    "employee_id": notification.employee_id,
                    "created_by": notification.created_by,
                    "receiver_role": notification.receiver_role,
                    "notification_metadata": notification.notification_metadata,
                    "employee": employee_dict
                }
            },
            user_id
        )
    except Exception as e:
        logger.error(f"Error sending websocket notification: {e}")

    return notification


async def create_notification_for_roles(
    db: Session,
    roles: List[str],
    type: str,
    title: str,
    message: str,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    employee_id: Optional[int] = None,
    created_by: Optional[int] = None,
    reference_id: Optional[int] = None,
    notification_metadata: Optional[dict] = None
) -> List[Notification]:
    from app.models.user import User, Role
    lower_roles = [r.lower() for r in roles]
    users = db.query(User).join(Role).filter(func.lower(Role.name).in_(lower_roles)).all()
    
    created_notifications = []
    for user in users:
        notification = await create_notification(
            db=db,
            user_id=user.id,
            type=type,
            title=title,
            message=message,
            reference_id=reference_id,
            category=category,
            severity=severity,
            employee_id=employee_id,
            created_by=created_by,
            receiver_role=user.role.name.lower() if user.role else None,
            notification_metadata=notification_metadata
        )
        created_notifications.append(notification)
        
    return created_notifications


def get_user_notifications(
    db: Session,
    user_id: int,
    limit: int = 50,
    page: int = 1,
    category: Optional[str] = None,
    is_read: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Notification]:
    from app.models.employee import Employee
    from app.models.user import User
    from datetime import datetime, timedelta, time
    from zoneinfo import ZoneInfo
    
    APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
    current = datetime.now(APP_TIMEZONE)
    yesterday_date = current.date() - timedelta(days=1)
    cutoff = datetime.combine(yesterday_date, time.min, tzinfo=APP_TIMEZONE)
    
    # Base query excluding login notifications across all roles
    query = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.deleted_at.is_(None),
        ~Notification.type.in_(["LOGIN", "LOGIN_ACTIVITY"]),
        ~func.coalesce(Notification.category, "").in_(["LOGIN", "LOGIN_ACTIVITY"])
    )

    # Check user role for role-specific notification filtering
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role and user.role.name.lower() in ["admin", "hr"]:
        # HR & Admin receive time off, regularization, alerts, and system notices; NOT routine employee punch-ins/outs
        query = query.filter(
            ~func.coalesce(Notification.category, "").in_(["PUNCH_IN", "PUNCH_OUT"])
        )
    
    if page == 1 and category is None and is_read is None and search is None:
        query = query.filter(
            or_(
                Notification.created_at >= cutoff,
                Notification.is_read == False
            )
        )
    
    if category:
        if category.upper() in ["ATTENDANCE", "LEAVE", "SYSTEM"]:
            query = query.filter(Notification.type == category.upper())
        else:
            query = query.filter(Notification.category == category.upper())
        
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
        
    if search:
        search_filter = f"%{search}%"
        query = query.outerjoin(Employee, Notification.employee_id == Employee.id).filter(
            or_(
                Notification.message.ilike(search_filter),
                Notification.title.ilike(search_filter),
                Employee.first_name.ilike(search_filter),
                Employee.last_name.ilike(search_filter)
            )
        )
        
    offset = (page - 1) * limit
    return (
        query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_unread_count(db: Session, user_id: int) -> int:
    from app.models.user import User
    query = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
        Notification.deleted_at.is_(None),
        ~Notification.type.in_(["LOGIN", "LOGIN_ACTIVITY"]),
        ~func.coalesce(Notification.category, "").in_(["LOGIN", "LOGIN_ACTIVITY"])
    )

    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role and user.role.name.lower() in ["admin", "hr"]:
        query = query.filter(
            ~func.coalesce(Notification.category, "").in_(["PUNCH_IN", "PUNCH_OUT"])
        )

    return query.count()


def mark_all_notifications_read(db: Session, user_id: int) -> int:
    from app.models.user import User
    update_query = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
        Notification.deleted_at.is_(None),
        ~Notification.type.in_(["LOGIN", "LOGIN_ACTIVITY"]),
        ~func.coalesce(Notification.category, "").in_(["LOGIN", "LOGIN_ACTIVITY"])
    )

    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role and user.role.name.lower() in ["admin", "hr"]:
        update_query = update_query.filter(
            ~func.coalesce(Notification.category, "").in_(["PUNCH_IN", "PUNCH_OUT"])
        )

    update_query.update(
        {Notification.is_read: True, Notification.read_at: func.now()},
        synchronize_session=False
    )
    db.commit()
    return get_unread_count(db, user_id)


def mark_notification_read(db: Session, user_id: int, notification_id: int) -> Optional[Notification]:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.deleted_at.is_(None)
        )
        .first()
    )
    if notification:
        notification.is_read = True
        notification.read_at = func.now()
        db.commit()
        db.refresh(notification)
    return notification


def clear_all_notifications(db: Session, user_id: int) -> bool:
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.deleted_at.is_(None)
    ).update(
        {Notification.deleted_at: func.now()},
        synchronize_session=False
    )
    db.commit()
    return True


def delete_notification(db: Session, user_id: int, notification_id: int) -> bool:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.deleted_at.is_(None)
        )
        .first()
    )
    if notification:
        notification.deleted_at = func.now()
        db.commit()
        return True
    return False

