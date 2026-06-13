import pytest
from datetime import time, date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.attendance import Attendance, AttendanceRegularizationRequest, AttendanceAuditTrail
from app.models.employee import Employee
from app.models.user import User, Role
from app.services.time_calculator import calculate_times
from app.services.scheduler_service import auto_checkout_forgotten_punches

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

# Setup memory sqlite for testing
@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed test data
        role_hr = Role(name="HR")
        role_emp = Role(name="Employee")
        db.add(role_hr)
        db.add(role_emp)
        db.commit()
        
        user_emp = User(email="emp@example.com", password_hash="pw", display_name="Emp", role_id=role_emp.id)
        user_hr = User(email="hr@example.com", password_hash="pw", display_name="HR", role_id=role_hr.id)
        db.add(user_emp)
        db.add(user_hr)
        db.commit()
        
        emp = Employee(
            user_id=user_emp.id, 
            first_name="John", 
            last_name="Doe", 
            employee_code="EMP001",
            official_email="emp@example.com",
            mobile="1234567890"
        )
        db.add(emp)
        db.commit()
        
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_auto_checkout_shift_end_progressive(db_session, monkeypatch):
    # Setup employee and today's attendance record
    emp = db_session.query(Employee).first()
    
    # 1. At 18:05: should send Shift End Reminder 1
    target_dt = datetime(2026, 6, 2, 18, 5, tzinfo=APP_TIMEZONE)
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return target_dt
    monkeypatch.setattr("app.services.scheduler_service.datetime", MockDatetime)
    
    attendance = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        punch_in=time(9, 0),
        is_working=1,
        status="WORKING"
    )
    db_session.add(attendance)
    db_session.commit()
    
    # Prevent session from being closed during test run
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr("app.services.scheduler_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr("app.services.scheduler_service.send_notification_sync", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.scheduler_service.send_websocket_message_sync", lambda *args, **kwargs: None)
    
    # Run scheduler job
    auto_checkout_forgotten_punches()
    
    # Check that shift_end_reminder_sent is updated to 1
    db_session.refresh(attendance)
    assert attendance.shift_end_reminder_sent == 1
    
    # 2. At 18:50: should trigger Auto-Checkout
    target_dt = datetime(2026, 6, 2, 18, 50, tzinfo=APP_TIMEZONE)
    
    auto_checkout_forgotten_punches()
    db_session.refresh(attendance)
    
    assert attendance.is_working == 0
    assert attendance.punch_out == time(18, 0)
    assert attendance.checkout_source == "AUTO"
    assert attendance.requires_regularization is True
    assert "AUTO_CHECKOUT" in attendance.flags
    assert "MISSED_PUNCH" in attendance.flags
    assert attendance.status == "PRESENT"

def test_approve_regularization_logic(db_session):
    emp = db_session.query(Employee).first()
    user_hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    
    # Setup auto-checked out attendance record
    attendance = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        punch_in=time(9, 0),
        punch_out=time(18, 0),
        is_working=0,
        checkout_source="AUTO",
        requires_regularization=True,
        flags=["AUTO_CHECKOUT", "MISSED_PUNCH"],
        status="PRESENT"
    )
    db_session.add(attendance)
    db_session.commit()
    
    # Create regularization request
    req = AttendanceRegularizationRequest(
        employee_id=emp.id,
        attendance_date=date(2026, 6, 2),
        requested_punch_in=time(9, 0),
        requested_punch_out=time(18, 30),
        reason_type="Forgot Check-out",
        reason_text="Left early for doctor appointment but forgot to check out",
        status="pending"
    )
    db_session.add(req)
    db_session.commit()
    
    # Approve request manually using the core business logic from routes
    req.status = "approved"
    req.reviewed_by = user_hr.id
    req.reviewed_at = datetime.now()
    
    # Update attendance
    attendance.punch_out = req.requested_punch_out
    attendance.checkout_source = "MANUAL"
    attendance.requires_regularization = False
    
    # Recompute times & flags
    calculate_times(attendance)
    
    current_flags = attendance.flags
    if "REGULARIZED" not in current_flags:
        current_flags.append("REGULARIZED")
    if "MISSED_PUNCH" in current_flags:
        current_flags.remove("MISSED_PUNCH")
    if "AUTO_CHECKOUT" in current_flags:
        current_flags.remove("AUTO_CHECKOUT")
    attendance.flags = current_flags
    
    db_session.commit()
    db_session.refresh(attendance)
    
    # Assertions
    assert attendance.requires_regularization is False
    assert attendance.checkout_source == "MANUAL"
    assert attendance.punch_out == time(18, 30)
    assert "REGULARIZED" in attendance.flags
    assert "MISSED_PUNCH" not in attendance.flags
    assert "AUTO_CHECKOUT" not in attendance.flags
