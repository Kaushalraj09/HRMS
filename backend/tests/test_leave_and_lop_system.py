import pytest
from datetime import date
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.employee import Employee
from app.models.master_data import LeaveType, Shift
from app.models.attendance import Attendance
from app.models.user import User, Role
from app.models.timeoff import TimeOffRequest
from app.models.payroll import SalaryStructure, EmployeeSalaryAssignment
from app.schemas.master_data import LeaveTypeUpdate
from app.seeds.seed_master_data import seed_master_data, seed_roles, seed_payroll_master_data
from app.services.leave_balance_service import LeaveBalanceService
from app.services.master_data_service import update_leave_type, delete_leave_type
from app.services import timeoff_service
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
    seed_payroll_master_data(db_session)
    yield db_session
    app.dependency_overrides.clear()


def create_test_employee(db, email="emp_test@example.com", code="EMP_TEST"):
    emp_role = db.query(Role).filter(Role.name == "Employee").first()
    user = User(email=email, password_hash="hash", display_name="Test Worker", role_id=emp_role.id)
    db.add(user)
    db.flush()
    shift = db.query(Shift).first()
    emp = Employee(
        user_id=user.id,
        employee_code=code,
        first_name="Test",
        last_name="Worker",
        official_email=email,
        mobile="9888888888",
        shift_id=shift.id if shift else None
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def test_system_defined_leave_types_immutability(db):
    """Verifies that UL and PL are system-defined and cannot be modified or deleted."""
    ul = db.query(LeaveType).filter(LeaveType.code == "UL").first()
    assert ul is not None
    assert ul.is_system_defined is True
    assert ul.is_paid is False
    assert ul.is_editable is False
    assert ul.is_deletable is False
    assert ul.annual_entitlement_days == 12

    pl = db.query(LeaveType).filter(LeaveType.code == "PL").first()
    assert pl is not None
    assert pl.is_system_defined is True
    assert pl.is_paid is True
    assert pl.is_deletable is False

    # Attempting to delete UL must fail with HTTP 400
    with pytest.raises(HTTPException) as exc_del_ul:
        delete_leave_type(db, ul.id)
    assert exc_del_ul.value.status_code == 400
    assert "cannot be deleted" in exc_del_ul.value.detail.lower()

    # Attempting to delete PL must fail with HTTP 400
    with pytest.raises(HTTPException) as exc_del_pl:
        delete_leave_type(db, pl.id)
    assert exc_del_pl.value.status_code == 400
    assert "cannot be deleted" in exc_del_pl.value.detail.lower()

    # Attempting to edit UL must fail with HTTP 400
    update_payload = LeaveTypeUpdate(
        name="Changed UL",
        code="UL",
        unit_type="full_day",
        default_balance_hours=80.0,
        requires_approval=True,
        is_active=True
    )
    with pytest.raises(HTTPException) as exc_edit_ul:
        update_leave_type(db, ul.id, update_payload)
    assert exc_edit_ul.value.status_code == 400
    assert "cannot be modified" in exc_edit_ul.value.detail.lower()


def test_employee_yearly_balance_initialization(db):
    """Verifies that employee balances initialize with 12d for UL and 18d for PL."""
    emp = create_test_employee(db)
    summary = timeoff_service.get_employee_leave_balances(db, emp.id, year=2026)

    assert summary["leave_year"] == 2026
    assert summary["unpaid_leave"]["allocated"] == 12
    assert summary["unpaid_leave"]["used"] == 0
    assert summary["unpaid_leave"]["remaining"] == 12

    assert summary["paid_leave"]["allocated"] == 18
    assert summary["paid_leave"]["used"] == 0
    assert summary["paid_leave"]["remaining"] == 18


def test_double_deduction_prevention_on_approved_paid_leave(db):
    """
    If an employee is marked ABSENT on a day that has approved Paid Leave,
    the attendance absence must NOT cause a salary deduction.
    """
    emp = create_test_employee(db)
    test_date = date(2026, 3, 10)

    # 1. Approved Paid Leave on test_date
    pl_req = TimeOffRequest(
        employee_id=emp.id,
        date=test_date,
        leave_type="Paid Leave",
        duration_hours=8.0,
        status="Approved"
    )
    db.add(pl_req)

    # 2. Attendance row marking ABSENT on same date
    att = Attendance(
        employee_id=emp.id,
        date=test_date,
        status="ABSENT"
    )
    db.add(att)
    db.commit()

    metrics = PayrollCalculationService.get_attendance_and_leave_metrics(
        db=db,
        employee_id=emp.id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31)
    )

    # Attendance ABSENT on approved leave date must be excluded from unexcused absent days
    assert metrics["paid_leave_days"] == 1.0
    assert metrics["approved_unpaid_leave_days"] == 0.0
    assert metrics["absent_days"] == 0.0
    assert metrics["lop_days"] == 0.0
    assert metrics["payable_days"] == 31.0


def test_double_deduction_prevention_on_approved_unpaid_leave(db):
    """
    If an employee has approved Unpaid Leave on a date that is also marked ABSENT,
    it must count as exactly 1 LOP day, NEVER 2.
    """
    emp = create_test_employee(db)
    test_date = date(2026, 3, 12)

    # 1. Approved Unpaid Leave on test_date
    ul_req = TimeOffRequest(
        employee_id=emp.id,
        date=test_date,
        leave_type="Unpaid Leave",
        duration_hours=8.0,
        status="Approved"
    )
    db.add(ul_req)

    # 2. Attendance row marking ABSENT on same date
    att = Attendance(
        employee_id=emp.id,
        date=test_date,
        status="ABSENT"
    )
    db.add(att)
    db.commit()

    metrics = PayrollCalculationService.get_attendance_and_leave_metrics(
        db=db,
        employee_id=emp.id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31)
    )

    # Exactly 1 LOP day, absent_days on this day is not added again
    assert metrics["approved_unpaid_leave_days"] == 1.0
    assert metrics["absent_days"] == 0.0
    assert metrics["lop_days"] == 1.0
    assert metrics["payable_days"] == 30.0


def test_lop_divisor_modes_calculation(db):
    """Verifies that LOP deduction adheres to configurable divisor modes."""
    emp = create_test_employee(db)

    # Use seeded standard salary structure
    struct = db.query(SalaryStructure).filter(SalaryStructure.code == "STD_EMP").first()
    assert struct is not None

    assign = EmployeeSalaryAssignment(
        employee_id=emp.id,
        salary_structure_id=struct.id,
        annual_ctc=600000.0,
        salary_basis="CTC",
        effective_from=date(2026, 1, 1),
        is_active=True
    )
    db.add(assign)

    # Add 2 days of approved unpaid leave in March (31 days)
    for d in [10, 11]:
        db.add(TimeOffRequest(
            employee_id=emp.id,
            date=date(2026, 3, d),
            leave_type="Unpaid Leave",
            duration_hours=8.0,
            status="Approved"
        ))
    db.commit()

    # 1. FIXED_30 mode: divisor = 30.0
    res_fixed = PayrollCalculationService.calculate_employee_payroll(
        db=db,
        employee_id=emp.id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        lop_divisor_mode="FIXED_30"
    )
    assert res_fixed["success"] is True
    fixed_gross = res_fixed["fixed_gross_salary"]
    assert fixed_gross > 0
    assert res_fixed["lop_deduction_amount"] == round((fixed_gross / 30.0) * 2, 2)

    # 2. CALENDAR_DAYS mode: divisor = 31.0
    res_cal = PayrollCalculationService.calculate_employee_payroll(
        db=db,
        employee_id=emp.id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        lop_divisor_mode="CALENDAR_DAYS"
    )
    assert res_cal["success"] is True
    assert res_cal["lop_deduction_amount"] == round((fixed_gross / 31.0) * 2, 2)

    # 3. WORKING_DAYS mode: divisor = 25.0
    res_work = PayrollCalculationService.calculate_employee_payroll(
        db=db,
        employee_id=emp.id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        period_working_days=25,
        lop_divisor_mode="WORKING_DAYS"
    )
    assert res_work["success"] is True
    assert res_work["lop_deduction_amount"] == round((fixed_gross / 25.0) * 2, 2)
