import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.payroll import (
    SalaryStructure,
    PayrollPeriod,
    PayrollRun,
    PayrollRecord,
)
from app.seeds.seed_master_data import seed_roles, seed_master_data, seed_payroll_master_data
from app.seeds.seed_demo_users import seed_users
from app.services.payroll_service import PayrollService
from app.schemas.payroll import EmployeeSalaryAssignmentCreate, PayrollRunCreate


@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    seed_roles(db)
    seed_master_data(db)
    seed_payroll_master_data(db)
    seed_users(db)

    # Explicitly ensure two employees with different departments exist
    emp1 = db.query(Employee).filter(Employee.status == "Active").first()
    emp1.department = "Engineering"

    emp2 = db.query(Employee).filter(Employee.status == "Active", Employee.id != emp1.id).first()
    if emp2:
        emp2.department = "Human Resources"

    db.commit()
    yield db
    db.close()


@pytest.fixture(name="client")
def fixture_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    hr_user = db_session.query(User).join(Role).filter(Role.name.in_(["HR", "Admin"])).first()
    app.dependency_overrides[get_current_user] = lambda: hr_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_employee_salaries_filter_all(client, db_session):
    res = client.get("/api/v1/payroll/employee-salaries")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2


def test_employee_salaries_filter_engineering(client, db_session):
    res = client.get("/api/v1/payroll/employee-salaries?department=Engineering")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["department"] == "Engineering"


def test_employee_salaries_filter_unknown_department(client, db_session):
    res = client.get("/api/v1/payroll/employee-salaries?department=NonExistentDept")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_employee_salaries_legacy_param_fallback(client, db_session):
    res = client.get("/api/v1/payroll/employee-salaries?department_id=Engineering")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["department"] == "Engineering"


def test_payroll_records_department_filter(client, db_session):
    # Set up salary assignment and run
    emp_eng = db_session.query(Employee).filter(Employee.department == "Engineering").first()
    emp_hr = db_session.query(Employee).filter(Employee.department == "Human Resources").first()
    structure = db_session.query(SalaryStructure).first()

    for emp in [emp_eng, emp_hr]:
        if emp:
            PayrollService.assign_employee_salary(
                db_session,
                EmployeeSalaryAssignmentCreate(
                    employee_id=emp.id,
                    salary_structure_id=structure.id,
                    salary_basis="CTC",
                    salary_type="Annual",
                    ctc_amount=600000.0,
                    effective_from=date(2026, 1, 1),
                ),
                user_id=1,
            )

    run_create = PayrollRunCreate(
        year=2026,
        month=9,
        selected_employee_ids=[emp_eng.id, emp_hr.id] if emp_eng and emp_hr else None,
        notes="Department test run"
    )
    run = PayrollService.execute_payroll_run(
        db_session,
        run_create,
        user_id=1,
    )

    # 1. No department filter -> returns all records
    res_all = client.get(f"/api/v1/payroll/runs/{run.id}/records")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] >= 2

    # 2. Filter by Engineering -> returns only Engineering records
    res_eng = client.get(f"/api/v1/payroll/runs/{run.id}/records?department=Engineering")
    assert res_eng.status_code == 200
    data_eng = res_eng.json()
    assert data_eng["total"] >= 1
    for item in data_eng["items"]:
        assert item["department"] == "Engineering"

    # 3. Filter by Human Resources -> returns only HR records
    res_hr = client.get(f"/api/v1/payroll/runs/{run.id}/records?department=Human Resources")
    assert res_hr.status_code == 200
    data_hr = res_hr.json()
    assert data_hr["total"] >= 1
    for item in data_hr["items"]:
        assert item["department"] == "Human Resources"

    # 4. Filter by NonExistent -> returns 0
    res_none = client.get(f"/api/v1/payroll/runs/{run.id}/records?department=NonExistent")
    assert res_none.status_code == 200
    data_none = res_none.json()
    assert data_none["total"] == 0
