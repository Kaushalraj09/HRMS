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
    # 3. Two days ago (before cutoff) notification
    n3 = Notification(user_id=user_id, type="TEST", title="3 Days Ago", message="test", created_at=now - timedelta(days=2))
    
    db.add_all([n1, n2, n3])
    db.commit()
    
    notifications = get_user_notifications(db, user_id=user_id)
    
    assert len(notifications) == 2
    assert notifications[0].title == "Today"
    assert notifications[1].title == "Yesterday"
    
    db.close()
