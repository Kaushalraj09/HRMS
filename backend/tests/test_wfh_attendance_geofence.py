import pytest
from datetime import date, datetime, time
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.employee import Employee
from app.models.master_data import LeaveType, WorkLocation
from app.models.user import User, Role
from app.models.timeoff import TimeOffRequest
from app.models.attendance import Attendance
from app.schemas.timeoff import TimeOffRequestCreate
from app.seeds.seed_master_data import seed_master_data, seed_roles
from app.services.leave_balance_service import LeaveBalanceService
from app.services import timeoff_service, attendance_service
from app.domain.attendance.services.punch_service import PunchService
from app.services.payroll_calculation_service import PayrollCalculationService


@pytest.fixture(name="db")
def fixture_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    seed_roles(db_session)
    seed_master_data(db_session)
    yield db_session
    app.dependency_overrides.clear()


def create_office_worker(db, email="wfh_test@example.com", code="WFH_EMP"):
    emp_role = db.query(Role).filter(Role.name == "Employee").first()
    user = User(email=email, password_hash="hash", display_name="Office Tester", role_id=emp_role.id)
    db.add(user)
    db.flush()
    emp = Employee(
        user_id=user.id,
        employee_code=code,
        first_name="Office",
        last_name="Tester",
        official_email=email,
        mobile="9777777777",
        work_location="Belagavi ICCC Office"
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def test_office_worker_punch_without_wfh_rejected_outside_radius(db):
    """
    Office worker with office coordinates (Belagavi: 15.8497, 74.4977)
    punching from far away coordinates (Bengaluru: 12.9716, 77.5946)
    without approved WFH must be rejected with 400 Bad Request.
    """
    emp = create_office_worker(db)
    today = date.today()

    # Attempt to punch in from far away coordinates
    with pytest.raises(HTTPException) as excinfo:
        PunchService.punch_in(
            db=db,
            employee_id=emp.id,
            work_mode="Office",
            latitude=12.9716,
            longitude=77.5946
        )
    assert excinfo.value.status_code == 400
    detail_str = str(excinfo.value.detail).lower()
    assert "geofence" in detail_str or "radius" in detail_str or "distance" in detail_str or "outside" in detail_str


def test_wfh_and_hourly_leave_requests_rejected(db):
    """
    Verifies that requesting Work From Home (WFH) or Hourly time off
    is rejected by timeoff_service with 400 Bad Request.
    """
    emp = create_office_worker(db, "wfh_rejected@example.com", "WFH_REJ_EMP")
    today = date.today()

    # 1. Requesting WFH should be rejected
    with pytest.raises(HTTPException) as exc_wfh:
        timeoff_service.request_timeoff(
            db=db,
            employee_id=emp.id,
            request=TimeOffRequestCreate(
                date=today,
                leave_type="Work From Home",
                duration_hours=8.0,
                reason="WFH test"
            )
        )
    assert exc_wfh.value.status_code == 400
    assert "not a leave category" in str(exc_wfh.value.detail).lower()

    # 2. Requesting Hourly time-off should be rejected
    with pytest.raises(HTTPException) as exc_hr:
        timeoff_service.request_timeoff(
            db=db,
            employee_id=emp.id,
            request=TimeOffRequestCreate(
                date=today,
                leave_type="Hourly",
                duration_hours=2.0,
                reason="Hourly test"
            )
        )
    assert exc_hr.value.status_code == 400
    assert "hourly" in str(exc_hr.value.detail).lower()


def test_designated_remote_worker_can_punch_remotely(db):
    """
    Assigned remote worker can punch in from remote coordinates.
    """
    emp_role = db.query(Role).filter(Role.name == "Employee").first()
    user = User(email="remote_emp@example.com", password_hash="hash", display_name="Remote Worker", role_id=emp_role.id)
    db.add(user)
    db.flush()
    emp = Employee(
        user_id=user.id,
        employee_code="REM_001",
        first_name="Remote",
        last_name="Worker",
        official_email="remote_emp@example.com",
        mobile="9888888888",
        work_location="Remote"
    )
    db.add(emp)
    db.commit()

    att = PunchService.punch_in(
        db=db,
        employee_id=emp.id,
        work_mode="Remote",
        latitude=12.9716,
        longitude=77.5946
    )
    assert att is not None
    assert att.work_mode == "Remote"
    assert att.punch_in is not None
