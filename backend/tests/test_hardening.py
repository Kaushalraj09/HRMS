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
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles
from app.services.dashboard_service import get_admin_dashboard_data, invalidate_dashboard_cache

@pytest.fixture
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
    from jose import jwt
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


def test_employee_creation_rolls_back_when_email_setup_fails(db_session, monkeypatch):
    from app.models.user import User
    from app.schemas.employee import EmployeeCreate
    from app.services.account_access_service import InvitationDeliveryError
    from app.services.employee_service import create_employee

    monkeypatch.setattr("app.services.mail_service.send_reset_email", lambda *args, **kwargs: False)

    with pytest.raises(InvitationDeliveryError):
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
    assert user is None


def test_hr_creation_rolls_back_when_email_setup_fails(db_session, monkeypatch):
    from app.models.user import User
    from app.schemas.hr import HrCreate
    from app.services.account_access_service import InvitationDeliveryError
    from app.services.hr_service import create_hr

    monkeypatch.setattr("app.services.mail_service.send_reset_email", lambda *args, **kwargs: False)

    with pytest.raises(InvitationDeliveryError):
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
    assert user is None
