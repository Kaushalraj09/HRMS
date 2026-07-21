import pytest
from datetime import time, date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.attendance import Attendance, AttendanceRegularizationRequest, AttendanceAuditTrail
from app.models.employee import Employee
from app.models.user import User, Role
from app.models.timeoff import TimeOffRequest
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
    
    # 2. At 18:50: should trigger Reminder 3 but NOT auto-checkout yet
    target_dt = datetime(2026, 6, 2, 18, 50, tzinfo=APP_TIMEZONE)
    
    auto_checkout_forgotten_punches()
    db_session.refresh(attendance)
    
    assert attendance.is_working == 1
    assert attendance.shift_end_reminder_sent == 3
    assert attendance.punch_out is None
    
    # 3. At 20:05: should trigger Auto-Checkout
    target_dt = datetime(2026, 6, 2, 20, 5, tzinfo=APP_TIMEZONE)
    
    auto_checkout_forgotten_punches()
    db_session.refresh(attendance)
    
    assert attendance.is_working == 0
    assert attendance.punch_out == time(18, 0)
    assert attendance.checkout_source == "AUTO"
    assert attendance.requires_regularization is True
    assert "AUTO_CHECKOUT" in attendance.flags
    assert "MISSED_PUNCH" in attendance.flags
    assert attendance.status == "PRESENT"

def test_auto_checkout_past_day_catchup(db_session, monkeypatch):
    emp = db_session.query(Employee).first()
    
    # Set current time to 10:00 AM today (June 3)
    target_dt = datetime(2026, 6, 3, 10, 0, tzinfo=APP_TIMEZONE)
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return target_dt
    monkeypatch.setattr("app.services.scheduler_service.datetime", MockDatetime)
    
    # Create an active record for yesterday (June 2) where punch-out was missed
    attendance = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        punch_in=time(9, 0),
        is_working=1,
        status="WORKING"
    )
    db_session.add(attendance)
    db_session.commit()
    
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr("app.services.scheduler_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr("app.services.scheduler_service.send_notification_sync", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.scheduler_service.send_websocket_message_sync", lambda *args, **kwargs: None)
    
    # Run scheduler job
    auto_checkout_forgotten_punches()
    db_session.refresh(attendance)
    
    # Should be immediately checked out for yesterday
    assert attendance.is_working == 0
    assert attendance.punch_out == time(18, 0)
    assert attendance.checkout_source == "AUTO"
    assert attendance.requires_regularization is True
    assert "AUTO_CHECKOUT" in attendance.flags
    assert "MISSED_PUNCH" in attendance.flags
    assert attendance.status == "PRESENT"

def test_auto_checkout_overtime_no_response(db_session, monkeypatch):
    emp = db_session.query(Employee).first()
    
    # 1. Start overtime today
    attendance = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        punch_in=time(9, 0),
        is_working=1,
        overtime_approved=True,
        overtime_start=time(18, 0),
        status="WORKING"
    )
    db_session.add(attendance)
    db_session.commit()
    
    # Set time to 20:05 today -> should send OT reminder 1
    target_dt = datetime(2026, 6, 2, 20, 5, tzinfo=APP_TIMEZONE)
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return target_dt
    monkeypatch.setattr("app.services.scheduler_service.datetime", MockDatetime)
    
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr("app.services.scheduler_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr("app.services.scheduler_service.send_notification_sync", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.scheduler_service.send_websocket_message_sync", lambda *args, **kwargs: None)
    
    auto_checkout_forgotten_punches()
    db_session.refresh(attendance)
    assert attendance.overtime_reminder_sent == 1
    assert attendance.is_working == 1
    
    # 2. Set time to 20:50 today -> should trigger auto-checkout to 20:00 with OVERTIME flag
    target_dt = datetime(2026, 6, 2, 20, 50, tzinfo=APP_TIMEZONE)
    auto_checkout_forgotten_punches()
    db_session.refresh(attendance)
    
    assert attendance.is_working == 0
    assert attendance.punch_out == time(20, 0)
    assert attendance.checkout_source == "AUTO"
    assert attendance.requires_regularization is True
    assert "AUTO_CHECKOUT" in attendance.flags
    assert "MISSED_PUNCH" in attendance.flags
    assert "OVERTIME" in attendance.flags
    assert attendance.status == "PRESENT"

def test_auto_checkout_extended_overtime_catchup(db_session, monkeypatch):
    emp = db_session.query(Employee).first()
    
    # Active record yesterday with extended overtime
    attendance = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        punch_in=time(9, 0),
        is_working=1,
        overtime_approved=True,
        overtime_extended=True,
        status="WORKING"
    )
    db_session.add(attendance)
    db_session.commit()
    
    # Run scheduler today
    target_dt = datetime(2026, 6, 3, 10, 0, tzinfo=APP_TIMEZONE)
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return target_dt
    monkeypatch.setattr("app.services.scheduler_service.datetime", MockDatetime)
    
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr("app.services.scheduler_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr("app.services.scheduler_service.send_notification_sync", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.scheduler_service.send_websocket_message_sync", lambda *args, **kwargs: None)
    
    auto_checkout_forgotten_punches()
    db_session.refresh(attendance)
    
    # Should be immediately checked out for yesterday to 22:00 without missed punch or regularization requirements
    assert attendance.is_working == 0
    assert attendance.punch_out == time(22, 0)
    assert attendance.checkout_source == "AUTO"
    assert attendance.requires_regularization is False
    assert "AUTO_CHECKOUT" in attendance.flags
    assert "OVERTIME" in attendance.flags
    assert "MISSED_PUNCH" not in attendance.flags


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


def test_continue_working_and_extend_overtime_endpoints(db_session):
    from app.api.v1.attendance_routes import continue_working, extend_overtime
    from app.models.employee import Employee
    from app.models.user import User
    from app.models.attendance import Attendance

    emp = db_session.query(Employee).first()
    user = db_session.query(User).filter(User.id == emp.user_id).first()

    # Create today's attendance record
    today_date = date.today()
    attendance = Attendance(
        employee_id=emp.id,
        date=today_date,
        punch_in=time(9, 0),
        is_working=1,
        status="WORKING"
    )
    db_session.add(attendance)
    db_session.commit()

    # Call continue_working
    res = continue_working(db=db_session, current_user=user)
    assert res is not None
    db_session.refresh(attendance)
    assert attendance.overtime_approved is True

    # Call extend_overtime
    res_extend = extend_overtime(db=db_session, current_user=user)
    assert res_extend is not None
    db_session.refresh(attendance)
    assert attendance.overtime_extended is True


def test_partial_day_with_approved_timeoff(db_session):
    # Get employee
    emp = db_session.query(Employee).first()
    
    # Create approved time-off request for today: 3 hours leave from 15:00 to 18:00
    req = TimeOffRequest(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        leave_type="Hourly",
        start_time=time(15, 0),
        end_time=time(18, 0),
        duration_hours=3.0,
        status="Approved"
    )
    db_session.add(req)
    db_session.commit()
    
    # Create attendance record: worked from 09:00 to 15:00 (gross = 6 hours, lunch overlap = 1 hour)
    # Net worked minutes = 360 - 60 = 300 minutes (5 hours)
    # Approved leave = 3 hours
    # Total shift credit = 5 + 3 = 8 hours (480 minutes) -> PRESENT status!
    attendance = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        punch_in=time(9, 0),
        punch_out=time(15, 0),
        is_working=0,
        status="WORKING"
    )
    db_session.add(attendance)
    db_session.commit()
    
    # Run calculate_times
    calculate_times(attendance)
    
    # Verify net working minutes is 300 (5 hours)
    assert attendance.total_working_minutes == 300
    # Verify break minutes is 60 (lunch) + 180 (leave) = 240
    assert attendance.break_minutes == 240
    # Verify status is PRESENT because net worked + leave = 8 hours
    assert attendance.status == "PRESENT"


def test_overlapping_timeoff(db_session):
    emp = db_session.query(Employee).first()
    
    # Approved hourly leave: 2 hours from 14:00 to 16:00
    req = TimeOffRequest(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        leave_type="Hourly",
        start_time=time(14, 0),
        end_time=time(16, 0),
        duration_hours=2.0,
        status="Approved"
    )
    db_session.add(req)
    db_session.commit()
    
    # Attendance: punch in 09:00, punch out 18:00 (gross = 9 hours, lunch = 1 hour)
    # Leave of 2 hours is during work time, so it overlaps.
    # Net worked time = 9 hours - 1 hour (lunch) - 2 hours (leave overlap) = 6 hours (360 mins)
    # Credited time = 6 hours + 2 hours leave = 8 hours (480 mins) -> PRESENT
    attendance = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 2),
        punch_in=time(9, 0),
        punch_out=time(18, 0),
        is_working=0,
        status="WORKING"
    )
    db_session.add(attendance)
    db_session.commit()
    
    calculate_times(attendance)
    
    # Net worked minutes is 360 (6 hours)
    assert attendance.total_working_minutes == 360
    # Break minutes is 60 (lunch) + 120 (leave) = 180
    assert attendance.break_minutes == 180
    # Status is PRESENT
    assert attendance.status == "PRESENT"

