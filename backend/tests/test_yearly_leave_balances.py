import pytest
from datetime import date
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.employee import Employee
from app.models.master_data import LeaveType
from app.models.user import User, Role
from app.models.timeoff import TimeOffRequest
from app.schemas.timeoff import TimeOffRequestCreate
from app.seeds.seed_master_data import seed_master_data, seed_roles
from app.services.leave_balance_service import LeaveBalanceService
from app.services import timeoff_service


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


def create_test_employee(db, email="emp_office@example.com", code="EMP_OFF", work_location="Belagavi Office"):
    emp_role = db.query(Role).filter(Role.name == "Employee").first()
    user = User(email=email, password_hash="hash", display_name="Test Worker", role_id=emp_role.id)
    db.add(user)
    db.flush()
    emp = Employee(
        user_id=user.id,
        employee_code=code,
        first_name="Office",
        last_name="Worker",
        official_email=email,
        mobile="9888888888",
        work_location=work_location
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def test_yearly_leave_balances_initialization(db):
    """Verifies that yearly balances are initialized from Master Data quotas and year 2026/2027 are independent."""
    emp = create_test_employee(db, "init_test@example.com", "INIT_EMP")

    # Initialize 2026
    balances_2026 = LeaveBalanceService.get_or_initialize_yearly_balances(db, emp.id, 2026)
    assert len(balances_2026) > 0

    cl_2026 = next(b for b in balances_2026 if b.leave_type.code == "CL")
    sl_2026 = next(b for b in balances_2026 if b.leave_type.code == "SL")
    el_2026 = next(b for b in balances_2026 if b.leave_type.code == "EL")

    assert cl_2026.allocated_days == 12.0
    assert cl_2026.available_days == 12.0
    assert sl_2026.allocated_days == 8.0
    assert el_2026.allocated_days == 18.0

    # Initialize 2027
    balances_2027 = LeaveBalanceService.get_or_initialize_yearly_balances(db, emp.id, 2027)
    cl_2027 = next(b for b in balances_2027 if b.leave_type.code == "CL")
    assert cl_2027.year == 2027
    assert cl_2027.available_days == 12.0


def test_leave_lifecycle_pending_approved_rejected(db):
    """
    Verifies that applying for leave places days into Pending and reduces Available.
    Approving transfers Pending into Used.
    Rejecting releases Pending back to Available.
    """
    emp = create_test_employee(db, "cycle@example.com", "CYCLE_EMP")
    LeaveBalanceService.get_or_initialize_yearly_balances(db, emp.id, 2026)

    # 1. Submit a 1-day Casual Leave request
    req1 = TimeOffRequestCreate(
        date=date(2026, 9, 15),
        leave_type="Casual Leave",
        duration_hours=8.0,
        reason="Personal work"
    )
    created1 = timeoff_service.request_timeoff(db, emp.id, req1, dispatch_event=False)
    assert created1.status == "Pending"

    summary = LeaveBalanceService.get_employee_balances_summary(db, emp.id, 2026)
    cl_summary = next(s for s in summary if s["code"] == "CL")
    assert cl_summary["pending_days"] == 1.0
    assert cl_summary["used_days"] == 0.0
    assert cl_summary["available_days"] == 11.0  # 12 - 1 pending = 11

    # 2. Reject request1 -> Pending released back to Available
    timeoff_service.approve_request(db, created1.id, "REJECT", admin_user_id=1, enforce_approval_stage=False)
    summary_after_reject = LeaveBalanceService.get_employee_balances_summary(db, emp.id, 2026)
    cl_after_reject = next(s for s in summary_after_reject if s["code"] == "CL")
    assert cl_after_reject["pending_days"] == 0.0
    assert cl_after_reject["used_days"] == 0.0
    assert cl_after_reject["available_days"] == 12.0

    # 3. Submit again and Approve
    req2 = TimeOffRequestCreate(
        date=date(2026, 9, 16),
        leave_type="Casual Leave",
        duration_hours=8.0,
        reason="Doctor visit"
    )
    created2 = timeoff_service.request_timeoff(db, emp.id, req2, dispatch_event=False)
    timeoff_service.approve_request(db, created2.id, "APPROVE", admin_user_id=1, enforce_approval_stage=False)

    summary_after_approve = LeaveBalanceService.get_employee_balances_summary(db, emp.id, 2026)
    cl_after_approve = next(s for s in summary_after_approve if s["code"] == "CL")
    assert cl_after_approve["pending_days"] == 0.0
    assert cl_after_approve["used_days"] == 1.0
    assert cl_after_approve["available_days"] == 11.0


def test_exceeding_leave_balance_rejected(db):
    """Verifies that requesting more days than available balance raises 400 Bad Request."""
    emp = create_test_employee(db, "over_balance@example.com", "OVER_EMP")
    LeaveBalanceService.get_or_initialize_yearly_balances(db, emp.id, 2026)

    # Set available balance to only 1 day for testing
    bals = LeaveBalanceService.get_or_initialize_yearly_balances(db, emp.id, 2026)
    cl_bal = next(b for b in bals if b.leave_type.code == "CL")
    cl_bal.allocated_days = 1.0
    cl_bal.available_days = 1.0
    db.commit()

    # First request: 1 day -> succeeds
    req1 = TimeOffRequestCreate(
        date=date(2026, 9, 21),
        leave_type="Casual Leave",
        duration_hours=8.0,
        reason="Day 1"
    )
    timeoff_service.request_timeoff(db, emp.id, req1, dispatch_event=False)

    # Second request: 1 day -> fails with Insufficient balance
    req2 = TimeOffRequestCreate(
        date=date(2026, 9, 22),
        leave_type="Casual Leave",
        duration_hours=8.0,
        reason="Day 2"
    )
    with pytest.raises(HTTPException) as excinfo:
        timeoff_service.request_timeoff(db, emp.id, req2, dispatch_event=False)
    assert excinfo.value.status_code == 400
    assert "Insufficient" in excinfo.value.detail

