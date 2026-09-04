from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.master_data import Shift
from app.models.user import Role, User
from app.schemas.master_data import ShiftCreate
from app.services.attendance_service import punch_in
from app.services.master_data_service import create_shift, update_shift


def test_shift_update_normalizes_explicit_null_attendance_rules():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    shift = create_shift(
        db,
        ShiftCreate(name="Default Rules Shift", code="DEFAULT-RULES"),
    )

    update_shift(
        db,
        shift.id,
        ShiftCreate(
            name="Default Rules Shift",
            code="DEFAULT-RULES",
            allow_early_punch_in=None,
            early_coming_minutes=None,
            punch_in_grace_minutes=None,
            shift_grace_minutes=None,
        ),
    )

    refreshed = db.query(Shift).filter(Shift.id == shift.id).one()
    assert refreshed.allow_early_punch_in is False
    assert refreshed.early_coming_minutes == 60
    assert refreshed.punch_in_grace_minutes == 10
    assert refreshed.shift_grace_minutes == 15

    db.close()


def test_legacy_null_shift_rules_do_not_break_attendance_punch_in():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    role = Role(name="Employee")
    db.add(role)
    db.flush()
    user = User(
        email="shift-rules@example.com",
        password_hash="hash",
        display_name="Shift Rules",
        role_id=role.id,
        status="Active",
    )
    db.add(user)
    db.flush()
    shift = Shift(
        name="Legacy Attendance Shift",
        code="LEGACY-ATTENDANCE",
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    db.add(shift)
    db.flush()
    employee = Employee(
        user_id=user.id,
        employee_code="SHIFT-001",
        first_name="Shift",
        last_name="Rules",
        official_email=user.email,
        mobile="9999999999",
        shift_id=shift.id,
        status="Active",
    )
    db.add(employee)
    db.commit()

    db.execute(
        text(
            "UPDATE shifts SET allow_early_punch_in = NULL, "
            "early_coming_minutes = NULL, punch_in_grace_minutes = NULL, "
            "shift_grace_minutes = NULL WHERE id = :shift_id"
        ),
        {"shift_id": shift.id},
    )
    db.commit()

    attendance = punch_in(
        db,
        employee.id,
        "Remote",
        custom_time=datetime(2026, 1, 1, 9, 5, tzinfo=ZoneInfo("Asia/Kolkata")),
    )

    record = db.query(Attendance).filter(Attendance.id == attendance.id).one()
    assert record.punch_in_grace_minutes == 10
    assert record.early_punch_window_minutes == 60
    assert record.shift_grace_minutes == 15

    db.close()


def test_punch_service_early_punch_in_allowed_and_disallowed():
    import pytest
    from fastapi import HTTPException
    from app.domain.attendance.services.punch_service import PunchService

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    role = Role(name="Employee")
    db.add(role)
    db.flush()
    user = User(
        email="early-punch@example.com",
        password_hash="hash",
        display_name="Early Punch User",
        role_id=role.id,
        status="Active",
    )
    db.add(user)
    db.flush()

    # Shift starts at 01:52 PM (13:52) with early punch allowed up to 30 mins
    shift = Shift(
        name="Afternoon Shift",
        code="AFT-01",
        start_time=time(13, 52),
        end_time=time(22, 0),
        allow_early_punch_in=True,
        early_coming_minutes=30,
        punch_in_grace_minutes=10,
    )
    db.add(shift)
    db.flush()

    emp = Employee(
        user_id=user.id,
        employee_code="EARLY-001",
        first_name="Early",
        last_name="Bird",
        official_email=user.email,
        mobile="9876543210",
        shift_id=shift.id,
        status="Active",
    )
    db.add(emp)
    db.commit()

    # 1. Punch in 12 minutes before shift start (13:40) -> Allowed!
    punch_time_ok = datetime(2026, 9, 4, 13, 40, tzinfo=ZoneInfo("Asia/Kolkata"))
    att = PunchService.punch_in(
        db,
        emp.id,
        "Remote",
        custom_time=punch_time_ok,
    )
    assert att.punch_in == time(13, 40)
    assert att.early_arrival_minutes == 12
    assert att.status == "WORKING"
    assert att.credited_work_start == time(13, 52)
    assert att.early_approval_status == "Approved"

    # Clean up attendance record for next test
    db.delete(att)
    db.commit()

    # 2. Punch in 45 minutes before shift start (13:07) -> Exceeds 30 min window -> Rejected!
    punch_time_too_early = datetime(2026, 9, 4, 13, 7, tzinfo=ZoneInfo("Asia/Kolkata"))
    with pytest.raises(HTTPException) as exc_info:
        PunchService.punch_in(
            db,
            emp.id,
            "Remote",
            custom_time=punch_time_too_early,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "OUTSIDE_EARLY_PUNCH_WINDOW"

    # 3. If allow_early_punch_in is False -> Early punch is completely disallowed
    shift.allow_early_punch_in = False
    db.commit()

    with pytest.raises(HTTPException) as exc_info2:
        PunchService.punch_in(
            db,
            emp.id,
            "Remote",
            custom_time=punch_time_ok,
        )
    assert exc_info2.value.status_code == 400
    assert exc_info2.value.detail["code"] == "EARLY_PUNCH_NOT_ALLOWED"
    assert "Cannot punch in before your shift starts at 01:52 PM" in exc_info2.value.detail["message"]

    # 4. Punch in within grace: 13:58 (6 mins late, within 10 min grace) -> status "WORKING", late_minutes = 0
    punch_within_grace = datetime(2026, 9, 4, 13, 58, tzinfo=ZoneInfo("Asia/Kolkata"))
    att_grace = PunchService.punch_in(
        db,
        emp.id,
        "Remote",
        custom_time=punch_within_grace,
    )
    assert att_grace.punch_in == time(13, 58)
    assert att_grace.late_minutes == 0
    assert att_grace.status == "WORKING"

    db.delete(att_grace)
    db.commit()

    # 5. Punch in past grace: 14:15 (23 mins late, exceeds 10 min grace) -> status "LATE", late_minutes = 23
    punch_late = datetime(2026, 9, 4, 14, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
    att_late = PunchService.punch_in(
        db,
        emp.id,
        "Remote",
        custom_time=punch_late,
    )
    assert att_late.punch_in == time(14, 15)
    assert att_late.late_minutes == 23
    assert att_late.status == "LATE"

    db.close()


def test_overall_shift_grace_and_grand_total_includes_lunch():
    from app.domain.attendance.services.punch_service import PunchService

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    role = Role(name="Employee")
    db.add(role)
    db.flush()
    user = User(
        email="duration-grace@example.com",
        password_hash="hash",
        display_name="Duration User",
        role_id=role.id,
        status="Active",
    )
    db.add(user)
    db.flush()

    # 8-hour shift (480 mins) with 15 min overall grace -> 465 mins (7h 45m) required
    # Unpaid lunch duration = 30 mins
    shift = Shift(
        name="8h Standard Shift",
        code="STD-8H",
        start_time=time(9, 0),
        end_time=time(17, 30),
        required_work_minutes=480,
        working_hours=8.0,
        shift_grace_minutes=15,
        lunch_duration_minutes=30,
    )
    db.add(shift)
    db.flush()

    emp = Employee(
        user_id=user.id,
        employee_code="DUR-001",
        first_name="Duration",
        last_name="Test",
        official_email=user.email,
        mobile="9876543211",
        shift_id=shift.id,
        status="Active",
    )
    db.add(emp)
    db.commit()

    # Punch in at 09:00, punch out at 17:15
    # Elapsed gross = 8 hours 15 mins (495 mins)
    # Lunch = 30 mins -> Net work = 465 mins (7 hours 45 mins)
    in_time = datetime(2026, 9, 4, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    out_time = datetime(2026, 9, 4, 17, 15, tzinfo=ZoneInfo("Asia/Kolkata"))

    PunchService.punch_in(db, emp.id, "Remote", custom_time=in_time)
    att_out = PunchService.punch_out(db, emp.id, "Remote", custom_time=out_time)

    # 1. Grand total includes lunch: 465 net work + 30 break = 495 mins
    assert att_out.total_working_minutes == 465
    assert att_out.break_minutes == 30
    assert att_out.grand_total_minutes == 495

    # 2. Reached 7h 45m (465 mins >= 480 - 15) -> No EARLY_EXIT flag, status is Present!
    assert "EARLY_EXIT" not in att_out.flags
    assert att_out.status == "Present"

    db.close()


def test_cross_midnight_auto_checkout_14_to_00():
    from app.domain.attendance.services.punch_service import PunchService
    from app.services.time_calculator import calculate_times

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    role = Role(name="Employee")
    db.add(role)
    db.flush()
    user = User(
        email="midnight-checkout@example.com",
        password_hash="hash",
        display_name="Midnight Checkout",
        role_id=role.id,
        status="Active",
    )
    db.add(user)
    db.flush()

    # Shift 14:00 to 22:00 (8h work)
    shift = Shift(
        name="Afternoon 14-22 Shift",
        code="AFT-14-22",
        start_time=time(14, 0),
        end_time=time(22, 0),
        required_work_minutes=480,
        working_hours=8.0,
        shift_grace_minutes=15,
        lunch_duration_minutes=30,
        max_overtime_minutes=120,
    )
    db.add(shift)
    db.flush()

    emp = Employee(
        user_id=user.id,
        employee_code="MID-001",
        first_name="Midnight",
        last_name="Worker",
        official_email=user.email,
        mobile="9876543299",
        shift_id=shift.id,
        status="Active",
    )
    db.add(emp)
    db.commit()

    # Punch in at 14:00 on 2026-09-03
    in_time = datetime(2026, 9, 3, 14, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    att = PunchService.punch_in(db, emp.id, "Remote", custom_time=in_time)
    att.overtime_approved = True
    db.commit()

    # Auto checkout occurs at 12:00 AM (00:00 midnight)
    out_time = datetime(2026, 9, 4, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    att.punch_out = time(0, 0)
    att.is_working = 0
    att.checkout_source = "AUTO"
    calculate_times(att)
    db.commit()

    # Must NOT be 0h 0m and must NOT be Absent!
    # Gross = 14:00 to 00:00 (10 hours = 600 mins)
    # Lunch = 30 mins -> Net work = 480 mins + 90 mins OT (or 570 mins total)
    assert att.total_working_minutes > 0
    assert att.grand_total_minutes >= 480
    assert att.status != "ABSENT"
    assert att.status in ["Present", "PRESENT"]

    db.close()



