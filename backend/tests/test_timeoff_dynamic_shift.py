import pytest
from datetime import date, time
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.master_data import Shift
from app.models.attendance import Attendance
from app.models.timeoff import TimeOffRequest
from app.schemas.timeoff import TimeOffRequestCreate, TimeOffApplyPayload
from app.services.timeoff_service import request_timeoff, apply_time_off
from app.services.attendance_service import get_today_state


@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed roles
    admin_role = Role(name="Admin")
    hr_role = Role(name="HR")
    emp_role = Role(name="Employee")
    db.add_all([admin_role, hr_role, emp_role])
    db.commit()

    # Seed users
    user_emp = User(
        email="emp_shift@example.com",
        password_hash="pw",
        display_name="Shift Emp",
        role_id=emp_role.id,
    )
    db.add(user_emp)
    db.commit()

    # Custom Shift: 10:00 to 19:00, lunch 13:30 to 14:30, half_day_hours=4.5
    custom_shift = Shift(
        name="Late Shift",
        code="LATE10",
        start_time=time(10, 0),
        end_time=time(19, 0),
        lunch_start_time=time(13, 30),
        lunch_end_time=time(14, 30),
        half_day_hours=Decimal("4.5"),
        working_hours=Decimal("8.0"),
        is_active=True,
    )
    db.add(custom_shift)
    db.commit()

    # Seed employee assigned to custom shift
    emp = Employee(
        user_id=user_emp.id,
        first_name="Custom",
        last_name="ShiftEmp",
        employee_code="EMPSHIFT01",
        official_email="emp_shift@example.com",
        mobile="9876543210",
        shift_id=custom_shift.id,
    )
    db.add(emp)
    db.commit()

    yield db
    db.close()


def test_dynamic_half_day_request_first_and_second_half(db_session):
    """Half-day request dynamically matches the employee's shift boundaries (10:00 - 13:30 & 14:30 - 19:00) and gets 4.5h duration."""
    emp = db_session.query(Employee).filter(Employee.official_email == "emp_shift@example.com").first()

    # 1. Request First Half
    first_half_req = TimeOffRequestCreate(
        date=date(2026, 9, 8),
        leave_type="Half-Day",
        start_time=time(10, 0),
        end_time=time(13, 30),
        duration_hours=4.5,
        reason="Morning appointment",
    )
    res_first = request_timeoff(db_session, emp.id, first_half_req, dispatch_event=False)
    assert res_first.leave_type == "Half-Day"
    assert res_first.duration_hours == 4.5
    assert res_first.status == "Pending"

    # 2. Request Second Half
    second_half_req = TimeOffRequestCreate(
        date=date(2026, 9, 9),
        leave_type="Half-Day",
        start_time=time(14, 30),
        end_time=time(19, 0),
        duration_hours=4.5,
        reason="Afternoon work",
    )
    res_second = request_timeoff(db_session, emp.id, second_half_req, dispatch_event=False)
    assert res_second.leave_type == "Half-Day"
    assert res_second.duration_hours == 4.5
    assert res_second.status == "Pending"


def test_dynamic_half_day_request_rejects_mismatched_timings(db_session):
    """When employee submits timings that do not match the shift's half-day sessions, it is rejected with 400."""
    emp = db_session.query(Employee).filter(Employee.official_email == "emp_shift@example.com").first()

    # Case A: Within shift hours (10:00-19:00), but arbitrary invalid session (11:00-15:00)
    invalid_session_req = TimeOffRequestCreate(
        date=date(2026, 9, 10),
        leave_type="Half-Day",
        start_time=time(11, 0),
        end_time=time(15, 0),
        duration_hours=4.0,
        reason="Arbitrary session times",
    )
    with pytest.raises(HTTPException) as excinfo_session:
        request_timeoff(db_session, emp.id, invalid_session_req, dispatch_event=False)

    assert excinfo_session.value.status_code == 400
    assert "Half-day time-off must match your shift session" in excinfo_session.value.detail

    # Case B: Outside shift hours (09:00 is before shift start 10:00)
    outside_shift_req = TimeOffRequestCreate(
        date=date(2026, 9, 10),
        leave_type="Half-Day",
        start_time=time(9, 0),
        end_time=time(13, 0),
        duration_hours=4.0,
        reason="Standard 9-1 on a 10-7 shift",
    )
    with pytest.raises(HTTPException) as excinfo_bounds:
        request_timeoff(db_session, emp.id, outside_shift_req, dispatch_event=False)

    assert excinfo_bounds.value.status_code == 400
    assert "falls outside of your assigned shift hours" in excinfo_bounds.value.detail


def test_dynamic_half_day_apply_time_off(db_session):
    """apply_time_off accepts valid shift session bounds and rejects mismatched bounds."""
    emp = db_session.query(Employee).filter(Employee.official_email == "emp_shift@example.com").first()

    target_date = date(2026, 12, 1)

    # 1. Valid First Half for custom shift (10:00 to 13:30)
    valid_payload = TimeOffApplyPayload(
        date=target_date,
        leave_type="Half-Day",
        start_time=time(10, 0),
        end_time=time(13, 30),
        reason="Doctor visit",
    )
    row, approved_hrs, remaining_hrs, _, _ = apply_time_off(
        db=db_session,
        employee_id=emp.id,
        payload=valid_payload,
    )
    assert row.leave_type == "Half-Day"
    assert row.duration_hours == 4.5
    assert row.status == "Pending"

    # 2. Invalid session raises HTTPException 400
    invalid_payload = TimeOffApplyPayload(
        date=target_date,
        leave_type="Half-Day",
        start_time=time(11, 0),
        end_time=time(15, 0),
        reason="Invalid shift session",
    )
    with pytest.raises(HTTPException) as excinfo:
        apply_time_off(
            db=db_session,
            employee_id=emp.id,
            payload=invalid_payload,
        )
    assert excinfo.value.status_code == 400
    assert "Half-day session must be either First Half" in excinfo.value.detail


def test_attendance_service_today_state_returns_shift_and_half_day_bounds(db_session):
    """AttendanceService.get_today_state must return shift bounds, 24-hr format strings, and halfDayHours."""
    emp = db_session.query(Employee).filter(Employee.official_email == "emp_shift@example.com").first()
    state = get_today_state(db_session, emp.id)

    assert state["shiftStart24"] == "10:00"
    assert state["shiftEnd24"] == "19:00"
    assert state["lunchStart24"] == "13:30"
    assert state["lunchEnd24"] == "14:30"
    assert state["halfDayHours"] == 4.5

    # Verify TodayAttendanceState schema serializes these fields properly
    from app.schemas.attendance import TodayAttendanceState
    schema_obj = TodayAttendanceState(**state)
    dumped = schema_obj.model_dump(by_alias=True)
    assert dumped["shiftStart24"] == "10:00"
    assert dumped["shiftEnd24"] == "19:00"
    assert dumped["lunchStart24"] == "13:30"
    assert dumped["lunchEnd24"] == "14:30"
    assert dumped["halfDayHours"] == 4.5


def test_custom_930_shift_half_day_leave_request(db_session):
    """An employee with shift 09:30 - 18:00 requesting First Half (09:30 - 13:30) must succeed."""
    emp_user = User(
        email="emp_930@example.com",
        password_hash="pw",
        display_name="930 Emp",
        role_id=3,
    )
    db_session.add(emp_user)
    db_session.commit()

    shift_930 = Shift(
        name="9:30 Shift",
        code="SHIFT930",
        start_time=time(9, 30),
        end_time=time(18, 0),
        lunch_start_time=time(13, 30),
        lunch_end_time=time(14, 0),
        half_day_hours=Decimal("4.0"),
        working_hours=Decimal("8.5"),
        is_active=True,
    )
    db_session.add(shift_930)
    db_session.commit()

    emp_930 = Employee(
        first_name="Test",
        last_name="930",
        employee_code="EMP930",
        official_email="emp_930@example.com",
        mobile="9876543211",
        user_id=emp_user.id,
        shift_id=shift_930.id,
    )
    db_session.add(emp_930)
    db_session.commit()

    req = TimeOffRequestCreate(
        date=date(2026, 9, 11),  # Friday
        leave_type="Half-Day",
        start_time=time(9, 30),
        end_time=time(13, 30),
        duration_hours=4.0,
        reason="Doctor Appointment",
    )
    created = request_timeoff(db_session, emp_930.id, req, dispatch_event=False)
    assert created.status == "Pending"
    assert created.start_time == time(9, 30)
    assert created.end_time == time(13, 30)

