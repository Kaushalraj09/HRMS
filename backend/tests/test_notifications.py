from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.core.database import Base
from app.models.notification import Notification
from app.services.notification_service import get_user_notifications

def test_get_user_notifications_two_days():
    # Setup in-memory SQLite DB
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    user_id = 1
    APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
    now = datetime.now(APP_TIMEZONE)
    
    # 1. Today's notification
    n1 = Notification(user_id=user_id, type="TEST", title="Today", message="test", created_at=now)
    # 2. Yesterday's notification (still within 2-day window)
    n2 = Notification(user_id=user_id, type="TEST", title="Yesterday", message="test", created_at=now - timedelta(days=1))
    # 3. Two days ago (before cutoff) notification, marked read
    n3 = Notification(user_id=user_id, type="TEST", title="3 Days Ago", message="test", created_at=now - timedelta(days=2), is_read=True)
    
    db.add_all([n1, n2, n3])
    db.commit()
    
    notifications = get_user_notifications(db, user_id=user_id)
    
    assert len(notifications) == 2
    assert notifications[0].title == "Today"
    assert notifications[1].title == "Yesterday"
    
    db.close()

def test_get_user_notifications_old_unread():
    # Setup in-memory SQLite DB
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    user_id = 1
    APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
    now = datetime.now(APP_TIMEZONE)
    
    # 1. Today's notification
    n1 = Notification(user_id=user_id, type="TEST", title="Today", message="test", created_at=now)
    # 2. Old but unread notification
    n2 = Notification(user_id=user_id, type="TEST", title="Old Unread", message="test", created_at=now - timedelta(days=5), is_read=False)
    
    db.add_all([n1, n2])
    db.commit()
    
    notifications = get_user_notifications(db, user_id=user_id)
    
    assert len(notifications) == 2
    db.close()


def test_create_notification_deduplication():
    import pytest
    import anyio
    from app.services.notification_service import create_notification

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    async def run_test():
        user_id = 1
        # First creation
        n1 = await create_notification(
            db=db,
            user_id=user_id,
            type="LEAVE",
            title="Time Off Request Rejected",
            message="Leave request rejected for Kaushal Raj.",
            reference_id=42
        )
        # Immediate duplicate creation attempt
        n2 = await create_notification(
            db=db,
            user_id=user_id,
            type="LEAVE",
            title="Time Off Request Rejected",
            message="Leave request rejected for Kaushal Raj.",
            reference_id=42
        )
        return n1, n2

    n1, n2 = anyio.run(run_test)
    assert n1.id == n2.id, "Expected second call to return existing notification without creating a duplicate row"

    count = db.query(Notification).filter(Notification.user_id == 1).count()
    assert count == 1, f"Expected exactly 1 notification in DB, found {count}"
    db.close()


def test_event_dispatcher_listener_deduplication():
    from app.domain.events.dispatcher import EventDispatcher, DomainEvent

    class SampleEvent(DomainEvent):
        pass

    def sample_listener(event):
        pass

    EventDispatcher.clear()
    EventDispatcher.register(SampleEvent, sample_listener)
    EventDispatcher.register(SampleEvent, sample_listener)

    listeners = EventDispatcher._listeners.get(SampleEvent, [])
    assert len(listeners) == 1, "Expected duplicate listener registrations to be ignored"
    EventDispatcher.clear()

