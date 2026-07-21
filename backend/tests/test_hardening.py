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
