from datetime import date, time, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models  # noqa: F401
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.master_data import Shift
from app.domain.attendance.services.punch_service import PunchService, is_test_punch_employee
from app.core.security import hash_password

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def test_test_user_punch_anytime_and_multiple_times():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    # Create roles
    emp_role = Role(name="Employee")
    db.add(emp_role)
    db.flush()

    # Create shift (strict 09:00 - 18:00 with no early punch allowed)
    shift = Shift(
        name="Morning Shift",
        code="MORN",
        start_time=time(9, 0),
        end_time=time(18, 0),
        allow_early_punch_in=False,
        early_coming_minutes=0,
        punch_in_grace_minutes=10,
    )
    db.add(shift)
    db.flush()

    # 1. Create a normal employee
    normal_user = User(
        email="normal_user@example.com",
        password_hash=hash_password("Pass@123"),
        display_name="Normal User",
        role_id=emp_role.id,
        status="Active"
    )
    db.add(normal_user)
    db.flush()

    normal_emp = Employee(
        user_id=normal_user.id,
        employee_code="0001",
        first_name="Normal",
        last_name="Emp",
        official_email="normal_user@example.com",
        mobile="9876543210",
        shift_type="Morning Shift",
        work_location="Remote",
    )
    db.add(normal_emp)
    db.flush()

    # 2. Create Vivek test employee
    test_user = User(
        email="TestVivekEmp@gmail.com",
        password_hash=hash_password("Testv@1234"),
        display_name="Vivek Employee",
        role_id=emp_role.id,
        status="Active"
    )
    db.add(test_user)
    db.flush()

    test_emp = Employee(
        user_id=test_user.id,
        employee_code="0002",
        first_name="Vivek",
        last_name="Employee",
        official_email="TestVivekEmp@gmail.com",
        mobile="9876543211",
        shift_type="Morning Shift",
        work_location="Remote",
    )
    db.add(test_emp)
    db.commit()

    assert is_test_punch_employee(normal_emp) is False
    assert is_test_punch_employee(test_emp) is True

    # Test Vivek Employee: Can punch in early (e.g. at 06:30 AM before 09:00 AM shift)
    custom_early = datetime(2026, 9, 22, 6, 30, tzinfo=APP_TIMEZONE)
    att1 = PunchService.punch_in(
        db, test_emp.id, work_mode="Remote", custom_time=custom_early
    )
    assert att1.is_working == 1
    assert att1.punch_in == time(6, 30)
    assert att1.punch_out is None

    # Test Vivek Employee: Can punch out (e.g. at 08:00 AM)
    custom_out1 = datetime(2026, 9, 22, 8, 0, tzinfo=APP_TIMEZONE)
    att1_out = PunchService.punch_out(
        db, test_emp.id, work_mode="Remote", custom_time=custom_out1
    )
    assert att1_out.is_working == 0
    assert att1_out.punch_out == time(8, 0)

    # Test Vivek Employee: MULTIPLE PUNCH IN! Punch in AGAIN on the same day (e.g. at 09:15 AM)
    custom_in2 = datetime(2026, 9, 22, 9, 15, tzinfo=APP_TIMEZONE)
    att2 = PunchService.punch_in(
        db, test_emp.id, work_mode="Remote", custom_time=custom_in2
    )
    assert att2.is_working == 1
    assert att2.punch_in == time(9, 15)
    assert att2.punch_out is None  # Reset for second cycle

    # Test Vivek Employee: Punch out AGAIN (e.g. at 12:00 PM)
    custom_out2 = datetime(2026, 9, 22, 12, 0, tzinfo=APP_TIMEZONE)
    att2_out = PunchService.punch_out(
        db, test_emp.id, work_mode="Remote", custom_time=custom_out2
    )
    assert att2_out.is_working == 0
    assert att2_out.punch_out == time(12, 0)

    # Test Vivek Employee: Third punch in cycle! (e.g. at 14:00)
    custom_in3 = datetime(2026, 9, 22, 14, 0, tzinfo=APP_TIMEZONE)
    att3 = PunchService.punch_in(
        db, test_emp.id, work_mode="Remote", custom_time=custom_in3
    )
    assert att3.is_working == 1
    assert att3.punch_in == time(14, 0)

    # Normal user is still blocked by shift window when punching in early
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        PunchService.punch_in(db, normal_emp.id, work_mode="Remote", custom_time=custom_early)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail.get("code") == "EARLY_PUNCH_NOT_ALLOWED"

    db.close()
