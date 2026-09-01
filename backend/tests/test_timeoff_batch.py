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
from app.models.timeoff import TimeOffRequest
from app.schemas.timeoff import (
    TimeOffRequestCreate,
    TimeOffRequestResponse,
    TimeOffBatchRequestCreate,
    TimeOffBatchResponse,
)


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
    user_emp = User(
        email="emp@example.com",
        password_hash="pw",
        display_name="Emp Test",
        role_id=emp_role.id,
    )
    user_hr = User(
        email="hr@example.com",
        password_hash="pw",
        display_name="HR Test",
        role_id=hr_role.id,
    )
    db.add_all([user_emp, user_hr])
    db.commit()

    # Seed employee
    emp = Employee(
        user_id=user_emp.id,
        first_name="Test",
        last_name="Employee",
        employee_code="EMP100",
        official_email="emp@example.com",
        mobile="1234567890",
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


def test_schema_import_and_instantiation():
    """Verify that schemas can be imported and instantiated without NameError."""
    req_resp = TimeOffRequestResponse(
        id=1,
        employee_id=10,
        employee_code="EMP100",
        date=date(2026, 9, 1),
        leave_type="Full-Day",
        duration_hours=8.0,
        status="pending",
        employee_name="Test Employee",
        batch_id="batch-123",
    )
    batch_resp = TimeOffBatchResponse(created_requests=[req_resp])
    assert len(batch_resp.created_requests) == 1
    assert batch_resp.created_requests[0].batch_id == "batch-123"


def test_single_timeoff_request(client, db_session):
    user_emp = db_session.query(User).filter(User.email == "emp@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_emp

    # 2026-09-08 is a Tuesday (working day)
    payload = {
        "date": "2026-09-08",
        "leave_type": "Full-Day",
        "duration_hours": 8.0,
        "reason": "Personal work",
    }
    response = client.post("/api/v1/timeoff/request", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["leave_type"] == "Full-Day"
    assert data["duration_hours"] == 8.0
    assert data["status"].lower() == "pending"
    assert data["batch_id"] is not None


def test_batch_timeoff_request(client, db_session):
    user_emp = db_session.query(User).filter(User.email == "emp@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_emp

    # 2026-09-08 (Tue), 2026-09-09 (Wed), 2026-09-10 (Thu) are working days
    payload = {
        "dates": ["2026-09-08", "2026-09-09", "2026-09-10"],
        "leave_type": "Full-Day",
        "duration_hours": 8.0,
        "reason": "Vacation",
    }
    response = client.post("/api/v1/timeoff/request/batch", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "created_requests" in data
    assert len(data["created_requests"]) == 3

    # All requests should share the same batch_id
    batch_ids = {r["batch_id"] for r in data["created_requests"]}
    assert len(batch_ids) == 1
    assert None not in batch_ids

    # Check database records
    db_records = db_session.query(TimeOffRequest).filter(
        TimeOffRequest.batch_id == list(batch_ids)[0]
    ).all()
    assert len(db_records) == 3


def test_timeoff_request_weekly_off_rejected(client, db_session):
    user_emp = db_session.query(User).filter(User.email == "emp@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_emp

    # 2026-09-06 is Sunday (weekly off)
    payload = {
        "date": "2026-09-06",
        "leave_type": "Full-Day",
        "duration_hours": 8.0,
        "reason": "Personal work",
    }
    response = client.post("/api/v1/timeoff/request", json=payload)
    assert response.status_code == 400
    assert "weekly off" in response.json()["detail"].lower()


def test_batch_timeoff_request_empty_dates(client, db_session):
    user_emp = db_session.query(User).filter(User.email == "emp@example.com").first()
    app.dependency_overrides[get_current_user] = lambda: user_emp

    payload = {
        "dates": [],
        "leave_type": "Full-Day",
        "duration_hours": 8.0,
        "reason": "Vacation",
    }
    response = client.post("/api/v1/timeoff/request/batch", json=payload)
    assert response.status_code == 400
