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


def test_office_worker_with_approved_wfh_can_punch_remotely(db):
    """
    Office worker with an APPROVED WFH request for today can punch in from ANY coordinates,
    the server detects approved WFH, sets effective work_mode to 'Remote', and bypasses geofencing.
    """
    emp = create_office_worker(db, "wfh_approved@example.com", "WFH_APP_EMP")
    today = date.today()

    # 1. Create and approve a WFH request for today
    LeaveBalanceService.get_or_initialize_yearly_balances(db, emp.id, today.year)
    wfh_req = TimeOffRequest(
        employee_id=emp.id,
        date=today,
        leave_type="Work From Home",
        duration_hours=8.0,
        status="Approved",
        reason="Approved WFH test"
    )
    db.add(wfh_req)
    db.commit()

    # 2. Today state should report hasApprovedWfh=True and workMode='Remote'
    today_state = attendance_service.get_today_state(db, emp.id)
    assert today_state["hasApprovedWfh"] is True
    assert today_state["workMode"] == "Remote"

    # 3. Punch in from far away coordinates (e.g. home/Bengaluru)
    att = PunchService.punch_in(
        db=db,
        employee_id=emp.id,
        work_mode="Office",  # Even if client passed "Office", server recognizes approved WFH and forces Remote
        latitude=12.9716,
        longitude=77.5946
    )

    assert att is not None
    assert att.work_mode == "Remote"
    assert att.punch_in is not None


def test_wfh_does_not_count_as_leave_in_payroll(db):
    """
    Verifies that WFH requests are excluded from paid_leave_days and unpaid_leave_days
    in PayrollCalculationService.
    """
    emp = create_office_worker(db, "wfh_payroll@example.com", "WFH_PAY_EMP")
    start = date(2026, 9, 1)
    end = date(2026, 9, 30)

    # Add approved WFH request
    wfh_req = TimeOffRequest(
        employee_id=emp.id,
        date=date(2026, 9, 10),
        leave_type="Work From Home",
        duration_hours=8.0,
        status="Approved",
        reason="WFH Day"
    )
    db.add(wfh_req)

    # Add approved Casual Leave request
    cl_req = TimeOffRequest(
        employee_id=emp.id,
        date=date(2026, 9, 15),
        leave_type="Casual Leave",
        duration_hours=8.0,
        status="Approved",
        reason="Real Leave Day"
    )
    db.add(cl_req)
    db.commit()

    metrics = PayrollCalculationService.get_attendance_and_leave_metrics(db, emp.id, start, end)
    # The paid leave days should only count the 1 Casual Leave day, NOT the WFH day
    assert metrics["paid_leave_days"] == 1.0
    assert metrics["unpaid_leave_days"] == 0.0
