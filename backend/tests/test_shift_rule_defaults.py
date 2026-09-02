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
