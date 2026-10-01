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
from app.models.attendance import Attendance
from app.models.timeoff import TimeOffRequest
from app.models.approval_task import ApprovalTask


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
    mgr_role = Role(name="Manager")
    emp_role = Role(name="Employee")
    db.add_all([admin_role, hr_role, mgr_role, emp_role])
    db.commit()

    # Seed users
    admin_user = User(email="admin@test.com", password_hash="hash", display_name="Admin User", role_id=admin_role.id)
    hr_user = User(email="hr@test.com", password_hash="hash", display_name="HR User", role_id=hr_role.id)
    mgr_a_user = User(email="mgr_a@test.com", password_hash="hash", display_name="Manager Alice", role_id=mgr_role.id)
    mgr_b_user = User(email="mgr_b@test.com", password_hash="hash", display_name="Manager Bob", role_id=mgr_role.id)
    emp1_user = User(email="emp1@test.com", password_hash="hash", display_name="Employee 1", role_id=emp_role.id)
    emp2_user = User(email="emp2@test.com", password_hash="hash", display_name="Employee 2", role_id=emp_role.id)
    db.add_all([admin_user, hr_user, mgr_a_user, mgr_b_user, emp1_user, emp2_user])
    db.commit()

    # Seed employee profiles
    mgr_a_emp = Employee(user_id=mgr_a_user.id, first_name="Alice", last_name="Mgr", employee_code="MGR001", official_email="mgr_a@test.com", mobile="1111111111")
    mgr_b_emp = Employee(user_id=mgr_b_user.id, first_name="Bob", last_name="Mgr", employee_code="MGR002", official_email="mgr_b@test.com", mobile="2222222222")
    emp1 = Employee(user_id=emp1_user.id, first_name="Emp", last_name="One", employee_code="EMP001", official_email="emp1@test.com", mobile="3333333333", reporting_manager_id=None)
    emp2 = Employee(user_id=emp2_user.id, first_name="Emp", last_name="Two", employee_code="EMP002", official_email="emp2@test.com", mobile="4444444444", reporting_manager_id=None)
    db.add_all([mgr_a_emp, mgr_b_emp, emp1, emp2])
    db.commit()

    yield db
    db.close()


@pytest.fixture(name="client")
def fixture_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_assign_and_revoke_manager_role(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@test.com").first()
    emp1 = db_session.query(Employee).filter(Employee.employee_code == "EMP001").first()
    app.dependency_overrides[get_current_user] = lambda: admin

    # Assign Manager role to Emp1
    res = client.post(f"/api/v1/employees/{emp1.id}/assign-manager")
    assert res.status_code == 200
    assert res.json()["user_role"].lower() == "manager"
    assert res.json()["is_manager"] is True

    # Revoke Manager role
    res = client.post(f"/api/v1/employees/{emp1.id}/revoke-manager")
    assert res.status_code == 200
    assert res.json()["user_role"].lower() == "employee"
    assert res.json()["is_manager"] is False


def test_team_assignment_and_manager_visibility(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@test.com").first()
    mgr_a_emp = db_session.query(Employee).filter(Employee.employee_code == "MGR001").first()
    emp1 = db_session.query(Employee).filter(Employee.employee_code == "EMP001").first()
    emp2 = db_session.query(Employee).filter(Employee.employee_code == "EMP002").first()
    app.dependency_overrides[get_current_user] = lambda: admin

    # Admin assigns emp1 to Manager Alice
    res = client.post(f"/api/v1/employees/{mgr_a_emp.id}/assign-team", json={"employee_ids": [emp1.id]})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["id"] == emp1.id

    # Switch login to Manager Alice
    mgr_a_user = db_session.query(User).filter(User.email == "mgr_a@test.com").first()
    app.dependency_overrides[get_current_user] = lambda: mgr_a_user

    # Alice views her team
    res = client.get("/api/v1/manager/team")
    assert res.status_code == 200
    team_ids = [e["id"] for e in res.json()["data"]]
    assert emp1.id in team_ids
    assert emp2.id not in team_ids

    # Alice tries to view details of Emp2 (not in her team) -> should be 403 Forbidden
    res = client.get(f"/api/v1/manager/team/{emp2.id}")
    assert res.status_code == 403


def test_manager_two_stage_leave_approval_workflow(client, db_session):
    mgr_a_emp = db_session.query(Employee).filter(Employee.employee_code == "MGR001").first()
    mgr_a_user = db_session.query(User).filter(User.email == "mgr_a@test.com").first()
    emp1 = db_session.query(Employee).filter(Employee.employee_code == "EMP001").first()
    emp1_user = db_session.query(User).filter(User.email == "emp1@test.com").first()
    hr_user = db_session.query(User).filter(User.email == "hr@test.com").first()

    # Assign emp1 to Manager Alice
    emp1.reporting_manager_id = mgr_a_emp.id
    db_session.commit()

    # 1. Emp1 requests time-off
    app.dependency_overrides[get_current_user] = lambda: emp1_user
    req_payload = {
        "date": str(date(2026, 10, 15)),
        "leave_type": "Full-Day",
        "duration_hours": 8.0,
        "reason": "Family function"
    }
    res = client.post("/api/v1/timeoff/request", json=req_payload)
    assert res.status_code == 200
    leave_id = res.json()["id"]

    # Verify ApprovalTask is assigned to manager
    task = db_session.query(ApprovalTask).filter(ApprovalTask.request_id == leave_id).first()
    assert task is not None
    assert task.assigned_role == "manager"
    assert task.status == "pending"

    # 2. Manager Alice sees the leave request
    app.dependency_overrides[get_current_user] = lambda: mgr_a_user
    res = client.get("/api/v1/manager/leave-requests")
    assert res.status_code == 200
    assert any(item["id"] == leave_id for item in res.json()["items"])

    # 3. Manager Alice approves the leave request
    res = client.post(f"/api/v1/manager/leave-requests/{leave_id}/approve", json={"comment": "Approved by Alice"})
    assert res.status_code == 200
    assert res.json()["approval_stage"] == "HR"

    # Verify task transitioned to HR stage
    db_session.refresh(task)
    assert task.assigned_role == "hr"
    assert task.status == "pending"
    assert task.manager_reviewed_by == mgr_a_user.id
    assert task.manager_decision_comment == "Approved by Alice"

    # 4. HR views requests and sees Manager decision
    app.dependency_overrides[get_current_user] = lambda: hr_user
    res = client.get("/api/v1/timeoff/pending")
    assert res.status_code == 200
    pending_item = next((item for item in res.json()["items"] if item["id"] == leave_id), None)
    assert pending_item is not None
    assert pending_item["approval_stage"] == "HR"
    assert pending_item["manager_decision"] == "Approved"
    assert pending_item["manager_comment"] == "Approved by Alice"

    # 5. HR final approval
    res = client.put(f"/api/v1/timeoff/approve/{leave_id}?action=APPROVE&comments=HR+Approved")
    assert res.status_code == 200
    assert res.json()["status"] == "Approved"


def test_manager_rejection_workflow(client, db_session):
    mgr_a_emp = db_session.query(Employee).filter(Employee.employee_code == "MGR001").first()
    mgr_a_user = db_session.query(User).filter(User.email == "mgr_a@test.com").first()
    emp1 = db_session.query(Employee).filter(Employee.employee_code == "EMP001").first()
    emp1_user = db_session.query(User).filter(User.email == "emp1@test.com").first()
    hr_user = db_session.query(User).filter(User.email == "hr@test.com").first()

    emp1.reporting_manager_id = mgr_a_emp.id
    db_session.commit()

    # Emp1 submits leave
    app.dependency_overrides[get_current_user] = lambda: emp1_user
    res = client.post("/api/v1/timeoff/request", json={
        "date": str(date(2026, 10, 20)),
        "leave_type": "Full-Day",
        "duration_hours": 8.0,
        "reason": "Personal"
    })
    leave_id = res.json()["id"]

    # Manager rejects with comment
    app.dependency_overrides[get_current_user] = lambda: mgr_a_user
    res = client.post(f"/api/v1/manager/leave-requests/{leave_id}/reject", json={"comment": "Team critical deadline"})
    assert res.status_code == 200
    assert res.json()["status"] == "Rejected"

    # HR can still see rejection and manager remarks in processed history
    app.dependency_overrides[get_current_user] = lambda: hr_user
    res = client.get("/api/v1/timeoff/history")
    assert res.status_code == 200
    rejected_item = next((item for item in res.json()["items"] if item["id"] == leave_id), None)
    assert rejected_item is not None
    assert rejected_item["status"] == "Rejected"
    assert rejected_item["manager_comment"] == "Team critical deadline"


def test_manager_unauthorized_endpoints(client, db_session):
    mgr_a_user = db_session.query(User).filter(User.email == "mgr_a@test.com").first()
    app.dependency_overrides[get_current_user] = lambda: mgr_a_user

    # Manager cannot access payroll
    res = client.get("/api/v1/payroll/dashboard")
    assert res.status_code == 403

    # Manager cannot access master data management
    res = client.get("/api/v1/master-data/departments")
    # Departments listing may be readable or restricted; let's check creating department
    res = client.post("/api/v1/master-data/departments", json={"name": "New Dept", "code": "ND"})
    assert res.status_code == 403


def test_manager_attendance_trend_periods(client, db_session):
    mgr_a_user = db_session.query(User).filter(User.email == "mgr_a@test.com").first()
    app.dependency_overrides[get_current_user] = lambda: mgr_a_user

    for period in ["Today", "This Month", "Last Month"]:
        res = client.get(f"/api/v1/manager/attendance-trend?period={period}")
        assert res.status_code == 200
        data = res.json()
        assert "labels" in data
        assert "present" in data
        assert "leave" in data
        assert "absent" in data
        assert len(data["labels"]) > 0
        assert len(data["present"]) == len(data["labels"])

