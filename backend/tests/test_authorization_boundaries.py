import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app import models
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.attendance import Attendance

from sqlalchemy.pool import StaticPool

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
    emp_role = Role(name="Employee")
    db.add_all([admin_role, hr_role, emp_role])
    db.commit()

    # Seed users
    user_emp1 = User(email="emp1@example.com", password_hash="pw", display_name="Emp 1", role_id=emp_role.id)
    user_emp2 = User(email="emp2@example.com", password_hash="pw", display_name="Emp 2", role_id=emp_role.id)
    user_hr = User(email="hr@example.com", password_hash="pw", display_name="HR User", role_id=hr_role.id)
    db.add_all([user_emp1, user_emp2, user_hr])
    db.commit()

    # Seed employees
    emp1 = Employee(user_id=user_emp1.id, first_name="Emp", last_name="One", employee_code="EMP001", official_email="emp1@example.com", mobile="1234567890")
    emp2 = Employee(user_id=user_emp2.id, first_name="Emp", last_name="Two", employee_code="EMP002", official_email="emp2@example.com", mobile="0987654321")
    db.add_all([emp1, emp2])
    db.commit()

    yield db
    db.close()

@pytest.fixture(name="client")
def fixture_client(db_session):
    # Override get_db
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_punch_in_own_attendance_success(client, db_session):
    # Get employee 1
    emp1 = db_session.query(Employee).filter(Employee.employee_code == "EMP001").first()
    user1 = db_session.query(User).filter(User.id == emp1.user_id).first()

    # Set logged in user as employee 1
    app.dependency_overrides[get_current_user] = lambda: user1

    payload = {
        "employee_id": emp1.id,
        "workMode": "Office"
    }
    
    response = client.post("/api/v1/attendance/punch-in", json=payload)
    assert response.status_code == 200
    assert response.json()["employeeId"] == emp1.id

def test_punch_in_other_attendance_forbidden(client, db_session):
    # Get employees
    emp1 = db_session.query(Employee).filter(Employee.employee_code == "EMP001").first()
    user1 = db_session.query(User).filter(User.id == emp1.user_id).first()
    emp2 = db_session.query(Employee).filter(Employee.employee_code == "EMP002").first()

    # Logged in as Employee 1, trying to punch for Employee 2
    app.dependency_overrides[get_current_user] = lambda: user1

    payload = {
        "employee_id": emp2.id,
        "workMode": "Office"
    }

    response = client.post("/api/v1/attendance/punch-in", json=payload)
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()

def test_punch_in_other_attendance_by_hr_allowed(client, db_session):
    # Get HR user and employee 2
    user_hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    emp2 = db_session.query(Employee).filter(Employee.employee_code == "EMP002").first()

    # Logged in as HR, trying to punch for Employee 2
    app.dependency_overrides[get_current_user] = lambda: user_hr

    payload = {
        "employee_id": emp2.id,
        "workMode": "Office"
    }

    response = client.post("/api/v1/attendance/punch-in", json=payload)
    assert response.status_code == 200
    assert response.json()["employeeId"] == emp2.id
