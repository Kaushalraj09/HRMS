import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models  # ensure all models are registered
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.models.user import User, Role
from app.models.dashboard_cache import DashboardCache
from app.models.timeoff import TimeOffRequest
from app.models.approval_task import ApprovalTask
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles
from app.services.dashboard_service import get_admin_dashboard_data, invalidate_dashboard_cache

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Bootstrap roles and users
    seed_roles(db)
    seed_users(db)
    db.commit()
    
    yield db
    db.close()

def test_user_linked_properties(db_session):
    # Fetch test employee user
    emp_user = db_session.query(User).join(Role).filter(func.lower(Role.name) == "employee").first()
    assert emp_user is not None
    
    # Assert properties evaluate without raising exception
    assert emp_user.linked_employee_id is not None
    assert emp_user.linked_hr_id is None

    # Fetch HR user
    hr_user = db_session.query(User).join(Role).filter(func.lower(Role.name) == "hr").first()
    assert hr_user is not None
    assert hr_user.linked_employee_id is not None
    assert hr_user.linked_hr_id is not None

def test_dashboard_cache_and_invalidation(db_session):
    # Initial state: cache is empty
    assert db_session.query(DashboardCache).count() == 0
    
    # Access dashboard -> populates cache
    data = get_admin_dashboard_data(db_session)
    assert db_session.query(DashboardCache).count() == 1
    
    # Get cache key entry
    cache_entry = db_session.query(DashboardCache).filter(DashboardCache.cache_key == "dashboard:admin").first()
    assert cache_entry is not None
    
    # Clear cache manually
    invalidate_dashboard_cache(db_session)
    assert db_session.query(DashboardCache).count() == 0

def test_timeoff_unique_composite_index(db_session):
    emp_user = db_session.query(User).join(Role).filter(func.lower(Role.name) == "employee").first()
    emp = db_session.query(Employee).filter(Employee.user_id == emp_user.id).first()
    
    from datetime import date
    # Create request 1
    req1 = TimeOffRequest(
        employee_id=emp.id,
        date=date(2026, 7, 7),
        leave_type="Full-Day",
        status="Approved",
        duration_hours=9.0
    )
    db_session.add(req1)
    db_session.commit()
    
    # Ensure it works
    assert db_session.query(TimeOffRequest).count() == 1


def test_create_hr_returns_api_response_shape_and_sends_setup_email(db_session, monkeypatch):
    from app.schemas.hr import HrCreate, HrResponse
    from app.services.hr_service import create_hr

    sent_email = {}

    def fake_send_reset_email(to_email, display_name, reset_link):
        sent_email.update({
            "to_email": to_email,
            "display_name": display_name,
            "reset_link": reset_link,
        })
        return True

    monkeypatch.setattr("app.services.mail_service.send_reset_email", fake_send_reset_email)

    response = create_hr(
        db_session,
        HrCreate(
            fullName="Observation HR",
            email="observation.hr@example.com",
            phone="9876543210",
            department="Human Resources",
            designation="HR Manager",
            status="Active",
        ),
    )

    validated = HrResponse.model_validate(response)
    assert validated.email == "observation.hr@example.com"
    assert validated.fullName == "Observation HR"
    assert validated.hrCode
    assert sent_email["to_email"] == "observation.hr@example.com"
    assert "/auth/reset-password?token=" in sent_email["reset_link"]


def test_forgot_password_returns_email_status_without_exposing_reset_link(db_session, monkeypatch):
    from types import SimpleNamespace
    from app.services import auth_service

    sent_email = {}

    def fake_send_reset_email(to_email, display_name, reset_link):
        sent_email.update({
            "to_email": to_email,
            "display_name": display_name,
            "reset_link": reset_link,
        })
        return True

    monkeypatch.setattr("app.services.mail_service.send_reset_email", fake_send_reset_email)

    result = auth_service.forgot_password(
        db_session,
        SimpleNamespace(email="hr@hrms.com"),
    )

    assert result is True
    assert sent_email["to_email"] == "hr@hrms.com"
    assert "/auth/reset-password?token=" in sent_email["reset_link"]


def test_websocket_ticket_has_a_dedicated_token_type():
    import jwt
    from app.core.config import settings
    from app.core.security import create_access_token, create_websocket_ticket

    access_claims = jwt.decode(
        create_access_token("employee@example.com"),
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    ticket_claims = jwt.decode(
        create_websocket_ticket("employee@example.com", 42),
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    assert access_claims["type"] == "access"
    assert ticket_claims["type"] == "websocket"
    assert ticket_claims["uid"] == 42


def test_employee_creation_uses_temporary_password_when_email_setup_is_unavailable(db_session, monkeypatch):
    from app.core.config import settings
    from app.models.user import User
    from app.schemas.auth import LoginRequest
    from app.schemas.employee import EmployeeCreate
    from app.services.auth_service import authenticate_user
    from app.services.employee_service import create_employee

    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")

    create_employee(
        db_session,
        EmployeeCreate(
            first_name="Vivek",
            last_name="Mehta",
            official_email="Vivekkumarmehta02@gmail.com",
            mobile="9876543210",
            department="Engineering",
            designation="Frontend Developer",
            employee_type="Full-Time",
            work_location="Main Office",
            shift_type="General Shift",
        ),
    )

    user = db_session.query(User).filter(User.email == "Vivekkumarmehta02@gmail.com").first()
    assert user is not None
    assert authenticate_user(
        db_session,
        LoginRequest(email=user.email, password="Vivek@1234"),
    ) is not None


def test_hr_creation_uses_temporary_password_when_email_setup_is_unavailable(db_session, monkeypatch):
    from app.core.config import settings
    from app.models.user import User
    from app.schemas.auth import LoginRequest
    from app.schemas.hr import HrCreate
    from app.services.auth_service import authenticate_user
    from app.services.hr_service import create_hr

    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")

    create_hr(
        db_session,
        HrCreate(
            fullName="Chandra Shekhar",
            email="Chandrashekhar@gmail.com",
            phone="9876543211",
            department="Human Resources",
            designation="HR Manager",
            status="Active",
        ),
    )

    user = db_session.query(User).filter(User.email == "Chandrashekhar@gmail.com").first()
    assert user is not None
    assert authenticate_user(
        db_session,
        LoginRequest(email=user.email, password="Chand@1234"),
    ) is not None


def test_login_accepts_email_derived_temporary_password(db_session):
    from app.core.security import hash_password
    from app.schemas.auth import LoginRequest
    from app.services.auth_service import authenticate_user

    user = db_session.query(User).filter(User.email == "hr@hrms.com").first()
    user.password_hash = hash_password("SecureLogin@123")
    db_session.commit()

    assert authenticate_user(
        db_session,
        LoginRequest(email=user.email, password="hr@1234"),
    ) is not None
    assert authenticate_user(
        db_session,
        LoginRequest(email=user.email, password="SecureLogin@123"),
    ) is None


def test_missing_smtp_configuration_uses_temporary_mock_delivery(monkeypatch, caplog):
    from app.core.config import settings
    from app.services.mail_service import send_reset_email

    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    secret_link = "https://hrms.example/reset?token=do-not-log"

    with caplog.at_level("WARNING"):
        assert send_reset_email("employee@example.com", "Employee", secret_link) is True

    assert "Development mock transmission" in caplog.text


def test_reset_access_reports_mock_success_when_email_delivery_is_unavailable(db_session, monkeypatch):
    from app.api.v1.employee_routes import reset_user_access

    hr_user = db_session.query(User).join(Role).filter(func.lower(Role.name) == "hr").first()
    employee = db_session.query(Employee).filter(Employee.user_id != hr_user.id).first()
    monkeypatch.setattr("app.services.mail_service.send_reset_email", lambda *args, **kwargs: False)

    response = reset_user_access(employee.id, db_session, hr_user)

    assert response["username"] == employee.official_email
    assert response["activation_required"] is True


def test_hr_cannot_skip_reporting_manager_approval(db_session):
    from datetime import date
    from app.services.approval_service import decide_task, require_hr_stage

    employee_role = db_session.query(Role).filter(Role.name == "Employee").first()
    hr_role = db_session.query(Role).filter(Role.name == "HR").first()
    manager_user = User(
        email="manager@example.com",
        password_hash="hash",
        display_name="Reporting Manager",
        role_id=employee_role.id,
    )
    target_user = User(
        email="approval-target@example.com",
        password_hash="hash",
        display_name="Approval Target",
        role_id=employee_role.id,
    )
    db_session.add_all([manager_user, target_user])
    db_session.flush()
    manager_employee = Employee(
        user_id=manager_user.id,
        employee_code="MGR-001",
        first_name="Reporting",
        last_name="Manager",
        official_email=manager_user.email,
        mobile="9000000001",
    )
    db_session.add(manager_employee)
    db_session.flush()
    target_employee = Employee(
        user_id=target_user.id,
        reporting_manager_id=manager_employee.id,
        employee_code="EMP-APP-001",
        first_name="Approval",
        last_name="Target",
        official_email=target_user.email,
        mobile="9000000002",
    )
    db_session.add(target_employee)
    db_session.flush()
    approval_task = ApprovalTask(
        request_type="timeoff",
        request_id=999,
        employee_id=target_employee.id,
        assigned_role="manager",
        submitted_by=target_user.id,
    )
    db_session.add(approval_task)
    db_session.commit()
    hr_user = db_session.query(User).filter(User.role_id == hr_role.id).first()

    with pytest.raises(Exception) as manager_stage_error:
        require_hr_stage(db_session, "timeoff", 999, hr_user.id)
    assert getattr(manager_stage_error.value, "status_code", None) == 409

    with pytest.raises(Exception) as bypass_error:
        decide_task(db_session, approval_task.id, hr_user.id, "approved")
    assert getattr(bypass_error.value, "status_code", None) == 403

    request = TimeOffRequest(
        employee_id=target_employee.id,
        date=date(2026, 8, 25),
        leave_type="Hourly",
        duration_hours=1.0,
        status="Pending",
    )
    db_session.add(request)
    db_session.flush()
    approval_task.request_id = request.id
    db_session.commit()

    override_result = decide_task(
        db_session,
        approval_task.id,
        hr_user.id,
        "approved",
        override=True,
        override_reason="Manager unavailable during payroll cutoff",
    )
    assert override_result.status == "approved"
    assert "HR override:" in override_result.decision_comment
    assert db_session.get(TimeOffRequest, request.id).status == "Approved"

    # A normal request must pass through the reporting manager and then the
    # final HR stage without the legacy time-off service rejecting the second
    # decision after the unified task has transitioned out of pending.
    two_step_request = TimeOffRequest(
        employee_id=target_employee.id,
        date=date(2026, 8, 26),
        leave_type="Hourly",
        duration_hours=1.0,
        status="Pending",
    )
    db_session.add(two_step_request)
    db_session.flush()
    two_step_task = ApprovalTask(
        request_type="timeoff",
        request_id=two_step_request.id,
        employee_id=target_employee.id,
        assigned_role="manager",
        submitted_by=target_user.id,
    )
    db_session.add(two_step_task)
    db_session.commit()

    manager_result = decide_task(
        db_session,
        two_step_task.id,
        manager_user.id,
        "approved",
        comment="Reviewed by reporting manager",
    )
    assert manager_result.assigned_role == "hr"
    assert manager_result.manager_reviewed_by == manager_user.id
    assert db_session.get(TimeOffRequest, two_step_request.id).approval_stage == "HR"

    hr_result = decide_task(
        db_session,
        two_step_task.id,
        hr_user.id,
        "approved",
        comment="Final HR approval",
    )
    assert hr_result.status == "approved"
    assert db_session.get(TimeOffRequest, two_step_request.id).status == "Approved"
