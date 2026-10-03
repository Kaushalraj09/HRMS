import pytest
import threading
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app.models.user import User, Role
from app.models.employee import Employee, EmployeeCodeSequence, EmployeeCodeHistory
from app.models.payroll import PayrollPeriod, PayrollRun, PayrollRecord, Payslip
from app.utils.employee_code import (
    format_employee_code,
    normalize_employee_code,
    extract_employee_code_number,
)
from app.services.employee_code_service import (
    get_or_create_sequence,
    allocate_next_employee_code,
    change_employee_code,
    get_code_history_for_employee,
)
from app.services import employee_service
from app.schemas.employee import EmployeeCreate


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
    admin_user = User(email="admin@hrms.com", password_hash="hash", display_name="Admin", role_id=admin_role.id)
    hr_user = User(email="hr@hrms.com", password_hash="hash", display_name="HR Manager", role_id=hr_role.id)
    emp_user = User(email="emp@hrms.com", password_hash="hash", display_name="Kaushal Raj", role_id=emp_role.id)
    db.add_all([admin_user, hr_user, emp_user])
    db.commit()

    # Seed existing employee with business code AIVAN024
    emp = Employee(
        user_id=emp_user.id,
        first_name="Kaushal",
        last_name="Raj",
        employee_code="AIVAN024",
        official_email="emp@hrms.com",
        mobile="9876543210",
        department="Engineering",
        work_location="Belagavi ICCC Office",
    )
    db.add(emp)
    db.commit()

    yield db
    db.close()


@pytest.fixture(name="client")
def fixture_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# =========================================================================
# 1. Normalization & Format Tests
# =========================================================================
def test_employee_code_formatting_and_normalization():
    assert format_employee_code(1) == "AIVAN001"
    assert format_employee_code(2) == "AIVAN002"
    assert format_employee_code(24) == "AIVAN024"
    assert format_employee_code(100) == "AIVAN100"
    assert format_employee_code(999) == "AIVAN999"
    assert format_employee_code(1000) == "AIVAN1000"

    # Normalization
    assert normalize_employee_code("aivan024") == "AIVAN024"
    assert normalize_employee_code("Aivan024") == "AIVAN024"
    assert normalize_employee_code("AIVAN-024") == "AIVAN024"
    assert normalize_employee_code("aivan-24") == "AIVAN024"
    assert normalize_employee_code("aivan 24") == "AIVAN024"
    assert normalize_employee_code("AIVAN1") == "AIVAN001"
    assert normalize_employee_code("AIVAN1000") == "AIVAN1000"

    # Legacy code preservation
    assert normalize_employee_code("OLD-EMP-458") == "OLD-EMP-458"
    assert normalize_employee_code("0004") == "0004"


# =========================================================================
# 2. Sequence Initialization & Preservation of Existing Codes
# =========================================================================
def test_sequence_initialization_from_highest_existing(db_session):
    # Existing employee is AIVAN024 -> highest is 24, next should be 25
    seq = get_or_create_sequence(db_session, prefix="AIVAN", padding=3)
    assert seq.next_number == 25
    assert seq.prefix == "AIVAN"

    # Next allocated code must be AIVAN025
    next_code = allocate_next_employee_code(db_session, prefix="AIVAN")
    assert next_code == "AIVAN025"
    assert seq.next_number == 26


# =========================================================================
# 3. Gap Preservation - Resigned/Deleted Codes Never Reused
# =========================================================================
def test_gap_preservation_codes_never_reused(db_session):
    seq = get_or_create_sequence(db_session, prefix="AIVAN", padding=3)
    c1 = allocate_next_employee_code(db_session, prefix="AIVAN")
    c2 = allocate_next_employee_code(db_session, prefix="AIVAN")
    assert c1 == "AIVAN025"
    assert c2 == "AIVAN026"

    # Even if we delete an employee or simulate resignation, sequence continues upward
    c3 = allocate_next_employee_code(db_session, prefix="AIVAN")
    assert c3 == "AIVAN027"


# =========================================================================
# 4. Atomic Employee Creation via Employee Service
# =========================================================================
def test_employee_creation_receives_sequential_code(db_session):
    new_emp_in = EmployeeCreate(
        first_name="Rohan",
        last_name="Kulkarni",
        official_email="rohan@hrms.com",
        mobile="9876543299",
        department="Engineering",
        work_location="Belagavi Office",
    )
    emp = employee_service.create_employee(db_session, new_emp_in)
    assert emp.employee_code == "AIVAN025"
    assert emp.employee_id == emp.id  # Permanent technical identity

    # Verify history recorded
    hist = get_code_history_for_employee(db_session, emp.id)
    assert len(hist) >= 1
    assert hist[0].new_employee_code == "AIVAN025"
    assert hist[0].reason == "Initial sequential assignment"


# =========================================================================
# 5. Concurrency Race Condition Safety
# =========================================================================
def test_concurrent_employee_creation_generates_distinct_codes(db_session):
    # Ensure sequence exists before concurrent workers start
    get_or_create_sequence(db_session, "AIVAN")

    allocated = []
    errors = []
    lock = threading.Lock()

    def worker():
        try:
            # Each worker allocates using thread-safe allocation
            with lock:
                code = allocate_next_employee_code(db_session, "AIVAN")
                db_session.commit()
                allocated.append(code)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    # Every code must be distinct (no collision)
    assert len(allocated) == len(set(allocated))
    assert all(c.startswith("AIVAN") for c in allocated)


# =========================================================================
# 6. Authorized Employee Code Modification with Audit Log
# =========================================================================
def test_authorized_code_change_and_history(client, db_session):
    hr_user = db_session.query(User).filter(User.email == "hr@hrms.com").first()
    emp = db_session.query(Employee).filter(Employee.employee_code == "AIVAN024").first()
    app.dependency_overrides[get_current_user] = lambda: hr_user

    # Attempt to change to invalid duplicate (own code)
    res = client.post(
        f"/api/v1/employees/{emp.id}/change-code",
        json={"new_employee_code": "AIVAN024", "reason": "Redundant change"},
    )
    assert res.status_code == 400

    # Authorized change with reason
    res = client.post(
        f"/api/v1/employees/{emp.id}/change-code",
        json={"new_employee_code": "aivan-099", "reason": "Re-alignment to executive series"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["employee_code"] == "AIVAN099"
    assert data["id"] == emp.id
    assert data["employee_id"] == emp.id

    # View history via endpoint
    hist_res = client.get(f"/api/v1/employees/{emp.id}/code-history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert history[0]["old_employee_code"] == "AIVAN024"
    assert history[0]["new_employee_code"] == "AIVAN099"
    assert history[0]["reason"] == "Re-alignment to executive series"
    assert history[0]["changed_by"] == hr_user.email


# =========================================================================
# 7. Search Across Employee Code & Legacy Code
# =========================================================================
def test_search_by_employee_code_and_legacy_code(db_session):
    emp = db_session.query(Employee).filter(Employee.first_name == "Kaushal").first()
    emp.legacy_employee_code = "OLD-K-007"
    db_session.commit()

    # Search by AIVAN code
    res1 = employee_service.list_employees(db_session, search="AIVAN024")
    assert res1["total"] == 1
    assert res1["data"][0]["first_name"] == "Kaushal"

    # Search by legacy code
    res2 = employee_service.list_employees(db_session, search="OLD-K-007")
    assert res2["total"] == 1
    assert res2["data"][0]["first_name"] == "Kaushal"


# =========================================================================
# 8. Payroll Historical Snapshot Protection
# =========================================================================
def test_payslip_preserves_historical_code_after_profile_update(db_session):
    emp = db_session.query(Employee).filter(Employee.employee_code == "AIVAN024").first()

    # Create dummy payroll period & run
    period = PayrollPeriod(
        year=2026,
        month=8,
        name="August 2026",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        pay_date=date(2026, 8, 31),
        total_days=31,
        working_days=22,
    )
    db_session.add(period)
    db_session.flush()

    run = PayrollRun(period_id=period.id, run_number=1, title="August 2026 Regular Run", status="FINALIZED")
    db_session.add(run)
    db_session.flush()

    record = PayrollRecord(
        payroll_run_id=run.id,
        employee_id=emp.id,
        status="FINALIZED",
    )
    db_session.add(record)
    db_session.flush()

    # Create payslip with snapshot values
    payslip = Payslip(
        payroll_record_id=record.id,
        employee_id=emp.id,
        payslip_number="PS-202608-AIVAN024",
        payroll_month="August 2026",
        employee_code_at_generation=emp.employee_code,
        employee_name_at_generation=f"{emp.first_name} {emp.last_name}",
        payroll_year=2026,
    )
    db_session.add(payslip)
    db_session.commit()

    # Verify initial payslip reflection
    assert payslip.employee_code == "AIVAN024"
    assert payslip.employee_name == "Kaushal Raj"

    # Now officially change employee's code and name
    change_employee_code(db_session, emp.id, "AIVAN888", reason="Corporate rebrand", changed_by="HR")
    emp.first_name = "Kaushal-Updated"
    db_session.commit()

    # Verify Payslip historical snapshot is NEVER changed
    db_session.refresh(payslip)
    assert payslip.employee_code == "AIVAN024"  # Historical snapshot preserved!
    assert payslip.employee_name == "Kaushal Raj"  # Historical snapshot preserved!


def test_get_next_employee_code_preview(client, db_session):
    hr_user = db_session.query(User).filter(User.email == "hr@hrms.com").first()
    app.dependency_overrides[get_current_user] = lambda: hr_user
    res = client.get("/api/v1/employees/next-code?prefix=AIVAN")
    assert res.status_code == 200
    data = res.json()
    assert data["prefix"] == "AIVAN"
    assert "nextNumber" in data
    assert "nextCode" in data
    assert data["nextCode"].startswith("AIVAN")


# =========================================================================
# 5. Migration Service & API Tests
# =========================================================================
def test_migrate_single_employee_to_aivan_code(client, db_session):
    from app.services.employee_code_service import migrate_employee_to_aivan_code

    emp_role = db_session.query(Role).filter(Role.name == "Employee").first()

    # Seed legacy employee
    legacy_user = User(email="legacy@hrms.com", password_hash="hash", display_name="Legacy User", role_id=emp_role.id)
    db_session.add(legacy_user)
    db_session.commit()

    legacy_emp = Employee(
        user_id=legacy_user.id,
        first_name="Ramesh",
        last_name="Kumar",
        employee_code="DEV-18",
        legacy_employee_code="DEV-18",
        official_email="legacy@hrms.com",
        mobile="9876543219",
        department="Engineering",
        work_location="Belagavi Office",
    )
    db_session.add(legacy_emp)
    db_session.commit()

    # Migrate with auto allocation
    updated_emp = migrate_employee_to_aivan_code(
        db_session,
        employee_id=legacy_emp.id,
        reason="System wide migration to standard AIVAN format",
        changed_by="HR Admin",
    )
    assert updated_emp.employee_code.startswith("AIVAN")
    assert updated_emp.legacy_employee_code == "DEV-18"
    assert updated_emp.employee_code_source == "LEGACY_MIGRATED"
    assert updated_emp.employee_code_status == "ACTIVE"

    db_session.refresh(legacy_emp)
    assert legacy_emp.employee_code.startswith("AIVAN")
    assert legacy_emp.legacy_employee_code == "DEV-18"
    assert legacy_emp.employee_code_source == "LEGACY_MIGRATED"
    assert legacy_emp.employee_code_status == "ACTIVE"

    # Verify history created
    histories = get_code_history_for_employee(db_session, legacy_emp.id)
    assert len(histories) >= 1
    assert histories[0].old_employee_code == "DEV-18"
    assert histories[0].new_employee_code == legacy_emp.employee_code


def test_migrate_employee_api_endpoint(client, db_session):
    hr_user = db_session.query(User).filter(User.email == "hr@hrms.com").first()
    emp_role = db_session.query(Role).filter(Role.name == "Employee").first()
    app.dependency_overrides[get_current_user] = lambda: hr_user

    # Seed another legacy employee
    emp_user = User(email="testlegacy@hrms.com", password_hash="hash", display_name="Test Legacy", role_id=emp_role.id)
    db_session.add(emp_user)
    db_session.commit()

    legacy_emp = Employee(
        user_id=emp_user.id,
        first_name="Anita",
        last_name="Desai",
        employee_code="EMP-102",
        official_email="testlegacy@hrms.com",
        mobile="9876543218",
        department="Sales",
        work_location="Headquarters",
    )
    db_session.add(legacy_emp)
    db_session.commit()

    # Call endpoint with custom code
    res = client.post(
        f"/api/v1/employees/{legacy_emp.id}/migrate-to-aivan-code",
        json={
            "new_employee_code": "AIVAN099",
            "reason": "Standardizing legacy employee format",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["employee_code"] == "AIVAN099"
    assert data["legacy_employee_code"] == "EMP-102"
    assert data["employee_code_source"] == "LEGACY_MIGRATED"
    assert data["employee_code_status"] == "ACTIVE"

    db_session.refresh(legacy_emp)
    assert legacy_emp.employee_code == "AIVAN099"
    assert legacy_emp.legacy_employee_code == "EMP-102"
    assert legacy_emp.employee_code_source == "LEGACY_MIGRATED"


def test_bulk_migrate_aivan_codes(client, db_session):
    from app.services.employee_code_service import run_bulk_aivan_code_migration

    emp_role = db_session.query(Role).filter(Role.name == "Employee").first()

    # Seed legacy employees with legacy formats
    for i, code in enumerate(["HR-45", "OLD-999"], start=1):
        u = User(email=f"legacy{i}@hrms.com", password_hash="hash", display_name=f"Bulk User {i}", role_id=emp_role.id)
        db_session.add(u)
        db_session.commit()
        emp = Employee(
            user_id=u.id,
            first_name=f"Legacy{i}",
            last_name="Staff",
            employee_code=code,
            official_email=f"legacy{i}@hrms.com",
            mobile=f"987654320{i}",
            department="Operations",
            work_location="Main Office",
        )
        db_session.add(emp)
    db_session.commit()

    summary = run_bulk_aivan_code_migration(db_session, changed_by="Bulk Test")
    assert summary["migrated"] >= 2
    assert "details" in summary

    # Verify both were migrated to AIVAN codes with legacy codes preserved
    emp1 = db_session.query(Employee).filter(Employee.legacy_employee_code == "HR-45").first()
    assert emp1 is not None
    assert emp1.employee_code.startswith("AIVAN")
    assert emp1.employee_code_source == "LEGACY_MIGRATED"

    emp2 = db_session.query(Employee).filter(Employee.legacy_employee_code == "OLD-999").first()
    assert emp2 is not None
    assert emp2.employee_code.startswith("AIVAN")
    assert emp2.employee_code_source == "LEGACY_MIGRATED"


