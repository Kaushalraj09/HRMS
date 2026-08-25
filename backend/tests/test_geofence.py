import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.geofence import calculate_haversine_distance, validate_employee_geofence
from app.models.employee import Employee
from app.models.master_data import WorkLocation
from app.models.user import User, Role
from app.seeds.seed_master_data import seed_master_data, seed_roles


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

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    seed_roles(db)
    seed_master_data(db)
    yield db
    app.dependency_overrides.clear()


def get_or_create_belagavi_employee(db):
    emp = db.query(Employee).filter(Employee.official_email == "test_belagavi@example.com").first()
    if not emp:
        role = db.query(Role).filter(Role.name == "Employee").first()
        user = User(email="test_belagavi@example.com", password_hash="hash", display_name="Test Belagavi", role_id=role.id)
        db.add(user)
        db.flush()
        emp = Employee(
            user_id=user.id,
            employee_code="TEST_BEL",
            first_name="Test",
            last_name="Belagavi",
            official_email="test_belagavi@example.com",
            mobile="9999999999",
            work_location="Belagavi ICCC Office"
        )
        db.add(emp)
        db.commit()
    return emp


def test_haversine_distance():
    # Exact same point -> 0 meters
    dist_zero = calculate_haversine_distance(15.8716667, 74.5085833, 15.8716667, 74.5085833)
    assert dist_zero == 0.0

    # Belagavi to Hubli (~87 km)
    dist_hubli = calculate_haversine_distance(15.8716667, 74.5085833, 15.3547222, 75.1341667)
    assert 80000 < dist_hubli < 95000

    # Small displacement (~20 meters)
    dist_small = calculate_haversine_distance(15.8716667, 74.5085833, 15.8718467, 74.5085833)
    assert 15 < dist_small < 25


def test_office_geofence_within_40m(db_session):
    emp = get_or_create_belagavi_employee(db_session)
    # Coordinates ~10 meters away from Belagavi office (15.8716667, 74.5085833)
    res = validate_employee_geofence(db_session, emp, 15.87175, 74.5085833)
    assert res["is_remote"] is False
    assert res["work_location_name"] == "Belagavi ICCC Office"
    assert res["distance_meters"] <= 40.0


def test_office_geofence_outside_40m(db_session):
    emp = get_or_create_belagavi_employee(db_session)
    # Coordinates ~150m away
    with pytest.raises(HTTPException) as exc_info:
        validate_employee_geofence(db_session, emp, 15.8730000, 74.5085833)

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["success"] is False
    assert "Belagavi ICCC Office" in detail["message"]
    assert detail["distance_meters"] > 40.0
    assert detail["allowed_radius_meters"] == 40


def test_office_geofence_missing_gps(db_session):
    emp = get_or_create_belagavi_employee(db_session)
    with pytest.raises(HTTPException) as exc_info:
        validate_employee_geofence(db_session, emp, None, None)

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert "GPS location access is required" in detail["message"]


def test_remote_employee_bypasses_geofence(db_session):
    emp = db_session.query(Employee).filter(Employee.official_email == "test_remote@example.com").first()
    if not emp:
        role = db_session.query(Role).filter(Role.name == "Employee").first()
        user = User(email="test_remote@example.com", password_hash="hash", display_name="Test Remote", role_id=role.id)
        db_session.add(user)
        db_session.flush()
        emp = Employee(
            user_id=user.id,
            employee_code="TEST_REM",
            first_name="Test",
            last_name="Remote",
            official_email="test_remote@example.com",
            mobile="9999999998",
            work_location="Remote"
        )
        db_session.add(emp)
        db_session.commit()

    # Remote employee without GPS
    res = validate_employee_geofence(db_session, emp, None, None)
    assert res["is_remote"] is True
    assert res["work_location_name"] == "Remote"


def test_unknown_work_location_fails_closed(db_session):
    emp = get_or_create_belagavi_employee(db_session)
    emp.work_location = "Unconfigured Office"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        validate_employee_geofence(db_session, emp, None, None)

    assert exc_info.value.status_code == 400
    assert "not configured" in exc_info.value.detail["message"]


def test_security_backend_enforcement(db_session):
    """
    Test that even if a Belagavi-assigned employee sends GPS coordinates of Hubli office,
    the backend enforces distance against Belagavi coordinates (from employee profile).
    """
    emp = get_or_create_belagavi_employee(db_session)
    # GPS coordinates of Hubli office (15.3547222, 75.1341667)
    with pytest.raises(HTTPException) as exc_info:
        validate_employee_geofence(db_session, emp, 15.3547222, 75.1341667)

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert detail["office"] == "Belagavi ICCC Office"
    assert detail["distance_meters"] > 80000
