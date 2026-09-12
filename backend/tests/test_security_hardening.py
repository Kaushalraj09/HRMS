import pytest
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from fastapi.testclient import TestClient

from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app import models
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.master_data import WorkLocation
from app.models.attendance import Attendance
from app.models.rate_limit import RateLimitRecord
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles
from app.core.security import create_access_token
from app.core.geofence import validate_employee_geofence, calculate_haversine_distance
from app.domain.attendance.services.punch_service import PunchService
from app.api.v1.auth_routes import _enforce_rate_limit, _clear_rate_limit
from app.main import app


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    seed_roles(db)
    seed_users(db)
    db.commit()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==========================================
# 1. Token Revocation & Versioning Tests
# ==========================================

def test_token_version_revocation(client, db_session):
    user = db_session.query(User).filter(User.email == "emp@hrms.com").first()
    assert user is not None

    # Generate token with current token_version
    valid_token = create_access_token(
        subject=user.email,
        additional_claims={"activeDashboard": "EMPLOYEE", "tv": user.token_version}
    )

    # Calling /api/v1/auth/me should succeed
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == user.email

    # Now increment token_version (simulating logout or password change)
    user.token_version += 1
    db_session.commit()

    # The old token must now be rejected immediately
    response_revoked = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response_revoked.status_code == 401
    assert "credentials" in response_revoked.json()["detail"].lower()


def test_logout_revokes_token(client, db_session):
    user = db_session.query(User).filter(User.email == "emp@hrms.com").first()
    initial_version = user.token_version

    token = create_access_token(
        subject=user.email,
        additional_claims={"activeDashboard": "EMPLOYEE", "tv": initial_version}
    )

    # Calling logout with bearer token
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_res.status_code == 200

    # Verify user token_version was incremented
    db_session.refresh(user)
    assert user.token_version > initial_version

    # Subsequent request with the same token must fail
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 401


# ==========================================
# 2. Multi-Worker DB Rate Limiting Tests
# ==========================================

def test_database_backed_rate_limiting(db_session):
    key = "test_rate_limit:127.0.0.1:user@example.com"
    _clear_rate_limit(db_session, key)

    # Max 3 attempts in 60-second window
    for _ in range(3):
        _enforce_rate_limit(db_session, key, max_attempts=3, window_seconds=60, lockout_seconds=300)

    # 4th attempt must raise 429 Too Many Requests
    with pytest.raises(HTTPException) as exc_info:
        _enforce_rate_limit(db_session, key, max_attempts=3, window_seconds=60, lockout_seconds=300)
    assert exc_info.value.status_code == 429

    # Verify RateLimitRecord in DB has locked_until set
    rec = db_session.query(RateLimitRecord).filter(RateLimitRecord.key == key).first()
    assert rec is not None
    assert rec.locked_until is not None

    # Clearing rate limit removes record
    _clear_rate_limit(db_session, key)
    assert db_session.query(RateLimitRecord).filter(RateLimitRecord.key == key).first() is None


# ==========================================
# 3. Geofence Anti-Spoofing & Sanity Tests
# ==========================================

def test_geofence_out_of_range_coordinates(db_session):
    emp = db_session.query(Employee).first()
    assert emp is not None

    # Latitude out of range (> 90)
    with pytest.raises(HTTPException) as exc_info:
        validate_employee_geofence(db_session, emp, current_lat=95.0, current_lon=75.0)
    assert exc_info.value.status_code == 400
    assert "range" in exc_info.value.detail["message"].lower()

    # Longitude out of range (> 180)
    with pytest.raises(HTTPException) as exc_info:
        validate_employee_geofence(db_session, emp, current_lat=20.0, current_lon=195.0)
    assert exc_info.value.status_code == 400
    assert "range" in exc_info.value.detail["message"].lower()


def test_geofence_null_island_rejection(db_session):
    emp = db_session.query(Employee).first()
    assert emp is not None

    # (0.0, 0.0) Null Island mock/uninitialized GPS
    with pytest.raises(HTTPException) as exc_info:
        validate_employee_geofence(db_session, emp, current_lat=0.0, current_lon=0.0)
    assert exc_info.value.status_code == 400
    assert "null island" in exc_info.value.detail["message"].lower() or "mock" in exc_info.value.detail["message"].lower()


def test_impossible_travel_detection(db_session):
    emp = db_session.query(Employee).first()
    assert emp is not None

    today = date(2026, 9, 12)
    # Configure an office location for employee
    work_loc = WorkLocation(
        name="Mumbai HQ",
        code="MUM01",
        latitude=19.0760,
        longitude=72.8777,
        geofence_radius_meters=1000.0,
        is_active=True,
        location_type="office"
    )
    db_session.add(work_loc)
    emp.work_location = "Mumbai HQ"
    db_session.commit()

    # Punch in at 09:00 in Mumbai (19.0760, 72.8777)
    punch_in_time = datetime(2026, 9, 12, 9, 0, 0, tzinfo=timezone.utc)
    att = PunchService.punch_in(
        db_session,
        employee_id=emp.id,
        work_mode="Office",
        latitude=19.0760,
        longitude=72.8777,
        custom_time=punch_in_time
    )
    assert att is not None

    # Try punching out 15 minutes later from Delhi (28.7041, 77.1025) ~1150 km away
    # Speed would be ~4600 km/h, which is impossible (> 250 km/h)
    punch_out_time = datetime(2026, 9, 12, 9, 15, 0, tzinfo=timezone.utc)
    with pytest.raises(HTTPException) as exc_info:
        PunchService.punch_out(
            db_session,
            employee_id=emp.id,
            work_mode="Office",
            latitude=28.7041,
            longitude=77.1025,
            custom_time=punch_out_time
        )
    assert exc_info.value.status_code == 400
    assert "impossible travel" in exc_info.value.detail["message"].lower()


# ==========================================
# 4. Security Headers Tests
# ==========================================

def test_security_headers_present(client):
    response = client.get("/api/v1/auth/me")
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "SAMEORIGIN"
    assert "strict-transport-security" in headers
    assert "max-age=31536000" in headers["strict-transport-security"]
    assert "content-security-policy" in headers
    assert "default-src 'self'" in headers["content-security-policy"]
