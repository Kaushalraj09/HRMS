import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.user import User, Role
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate
from app.services.employee_service import create_employee, delete_employee, list_employees
from app.services.dashboard_service import get_admin_dashboard_data, get_hr_dashboard_data, invalidate_dashboard_cache

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        role_admin = Role(name="admin")
        role_hr = Role(name="hr")
        role_emp = Role(name="employee")
        db.add_all([role_admin, role_hr, role_emp])
        db.commit()
        yield db
    finally:
        db.close()

def test_deleted_employee_excluded_from_total_count(db_session, monkeypatch):
    monkeypatch.setattr("app.services.mail_service.send_reset_email", lambda *a, **kw: True)
    emp1_in = EmployeeCreate(
        first_name="Active",
        last_name="Worker",
        official_email="active.worker@hrms.com",
        mobile="9876543210",
        department="Engineering",
        designation="Software Engineer",
        employee_type="Full-Time"
    )
    emp2_in = EmployeeCreate(
        first_name="ToBeDeleted",
        last_name="Worker",
        official_email="tobedeleted.worker@hrms.com",
        mobile="9876543211",
        department="Engineering",
        designation="QA Engineer",
        employee_type="Full-Time"
    )

    emp1 = create_employee(db_session, emp1_in)
    emp2 = create_employee(db_session, emp2_in)

    # Invalidate dashboard cache to start fresh
    invalidate_dashboard_cache(db_session)

    # Initial employee count check
    initial_list = list_employees(db_session)
    admin_dash_initial = get_admin_dashboard_data(db_session)
    hr_dash_initial = get_hr_dashboard_data(db_session)

    assert initial_list["total"] >= 2
    admin_total_initial = int(next(c["value"] for c in admin_dash_initial["cards"] if c["label"] == "Total Employees"))
    assert admin_total_initial >= 2
    assert hr_dash_initial["totalEmployees"] >= 2

    # Delete emp2
    success = delete_employee(db_session, emp2.id)
    assert success is True

    # Post-deletion employee count check
    post_list = list_employees(db_session)
    admin_dash_post = get_admin_dashboard_data(db_session)
    hr_dash_post = get_hr_dashboard_data(db_session)

    assert post_list["total"] == initial_list["total"] - 1
    admin_total_post = int(next(c["value"] for c in admin_dash_post["cards"] if c["label"] == "Total Employees"))
    assert admin_total_post == admin_total_initial - 1
    assert hr_dash_post["totalEmployees"] == hr_dash_initial["totalEmployees"] - 1

    # Verify deleted employee ID is not present in employee list
    returned_ids = [e["id"] for e in post_list["data"]]
    assert emp2.id not in returned_ids
