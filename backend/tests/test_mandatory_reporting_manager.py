import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app.models.user import User, Role
from app.models.employee import Employee

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed roles
    admin_role = Role(name="Admin")
    hr_role = Role(name="HR")
    manager_role = Role(name="Manager")
    emp_role = Role(name="Employee")
    db.add_all([admin_role, hr_role, manager_role, emp_role])
    db.commit()

    # Seed HR user
    user_hr = User(email="hr@hrms.com", password_hash="pw", display_name="HR Admin", role_id=hr_role.id, status="Active")
    # Seed Manager user & employee profile
    user_mgr = User(email="mgr@hrms.com", password_hash="pw", display_name="Manager Bob", role_id=manager_role.id, status="Active")
    db.add_all([user_hr, user_mgr])
    db.commit()

    manager_emp = Employee(
        user_id=user_mgr.id,
        first_name="Bob",
        last_name="Manager",
        employee_code="AIVAN001",
        official_email="mgr@hrms.com",
        mobile="9876543210",
        work_location="Main Office",
        status="Active"
    )
    db.add(manager_emp)
    db.commit()

    yield db
    db.close()

@pytest.fixture(name="client")
def fixture_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    hr_user = db_session.query(User).filter(User.email == "hr@hrms.com").first()
    app.dependency_overrides[get_current_user] = lambda: hr_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_employee_missing_manager_fails(client):
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "official_email": "alice.smith@hrms.com",
        "mobile": "9998887776",
        "work_location": "Main Office",
        "department": "Engineering",
        "designation": "Software Engineer",
        "employee_type": "Full-Time"
    }
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 400
    assert "Assigning a reporting manager is mandatory" in response.json().get("detail", "")

def test_create_employee_invalid_manager_fails(client):
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "official_email": "alice.smith@hrms.com",
        "mobile": "9998887776",
        "work_location": "Main Office",
        "department": "Engineering",
        "designation": "Software Engineer",
        "employee_type": "Full-Time",
        "reporting_manager_id": 99999
    }
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 400
    assert "Selected reporting manager does not exist" in response.json().get("detail", "")

def test_create_employee_with_valid_manager_succeeds(client, db_session):
    manager = db_session.query(Employee).filter(Employee.employee_code == "AIVAN001").first()
    assert manager is not None

    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "official_email": "alice.smith@hrms.com",
        "mobile": "9998887776",
        "work_location": "Main Office",
        "department": "Engineering",
        "designation": "Software Engineer",
        "employee_type": "Full-Time",
        "reporting_manager_id": manager.id
    }
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["reporting_manager_id"] == manager.id
    assert data["official_email"] == "alice.smith@hrms.com"


def test_fresh_db_create_first_manager_without_reporting_manager_succeeds(client):
    payload = {
        "first_name": "Carol",
        "last_name": "Director",
        "official_email": "carol.director@hrms.com",
        "mobile": "9887766554",
        "work_location": "Main Office",
        "department": "Executive",
        "designation": "Engineering Director",
        "employee_type": "Full-Time",
        "role": "manager"
    }
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["reporting_manager_id"] is None
    assert data["official_email"] == "carol.director@hrms.com"


def test_create_hr_without_reporting_manager_succeeds(client):
    payload = {
        "first_name": "Helen",
        "last_name": "Resource",
        "official_email": "helen.hr@hrms.com",
        "mobile": "9871122334",
        "work_location": "Main Office",
        "department": "Human Resources",
        "designation": "HR Generalist",
        "employee_type": "Full-Time",
        "role": "hr"
    }
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["reporting_manager_id"] is None


def test_update_employee_with_invalid_manager_fails(client, db_session):
    manager = db_session.query(Employee).filter(Employee.employee_code == "AIVAN001").first()
    # Create employee
    payload = {
        "first_name": "Dave",
        "last_name": "Test",
        "official_email": "dave.test@hrms.com",
        "mobile": "9112233445",
        "work_location": "Main Office",
        "department": "Engineering",
        "designation": "Dev",
        "employee_type": "Full-Time",
        "reporting_manager_id": manager.id
    }
    create_res = client.post("/api/v1/employees", json=payload)
    assert create_res.status_code == 200
    emp_id = create_res.json()["id"]

    # Try updating with invalid manager
    upd_res = client.put(f"/api/v1/employees/{emp_id}", json={"reporting_manager_id": 99999})
    assert upd_res.status_code == 400
    assert "Selected reporting manager does not exist" in upd_res.json()["detail"]


def test_update_employee_with_self_manager_fails(client, db_session):
    manager = db_session.query(Employee).filter(Employee.employee_code == "AIVAN001").first()
    payload = {
        "first_name": "Eve",
        "last_name": "Self",
        "official_email": "eve.self@hrms.com",
        "mobile": "9112233446",
        "work_location": "Main Office",
        "department": "Engineering",
        "designation": "Dev",
        "employee_type": "Full-Time",
        "reporting_manager_id": manager.id
    }
    create_res = client.post("/api/v1/employees", json=payload)
    assert create_res.status_code == 200
    emp_id = create_res.json()["id"]

    # Try setting self as manager
    upd_res = client.put(f"/api/v1/employees/{emp_id}", json={"reporting_manager_id": emp_id})
    assert upd_res.status_code == 400
    assert "cannot be their own reporting manager" in upd_res.json()["detail"]


def test_update_employee_remove_manager_fails(client, db_session):
    manager = db_session.query(Employee).filter(Employee.employee_code == "AIVAN001").first()
    payload = {
        "first_name": "Frank",
        "last_name": "Norm",
        "official_email": "frank.norm@hrms.com",
        "mobile": "9112233447",
        "work_location": "Main Office",
        "department": "Engineering",
        "designation": "Dev",
        "employee_type": "Full-Time",
        "reporting_manager_id": manager.id
    }
    create_res = client.post("/api/v1/employees", json=payload)
    assert create_res.status_code == 200
    emp_id = create_res.json()["id"]

    # Try removing manager on employee
    upd_res = client.put(f"/api/v1/employees/{emp_id}", json={"reporting_manager_id": None})
    assert upd_res.status_code == 400
    assert "mandatory for employees" in upd_res.json()["detail"]

