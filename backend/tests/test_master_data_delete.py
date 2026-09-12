import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.core.database import SessionLocal
from app.models.master_data import Department, Designation, Shift, WorkLocation, LeaveType, Holiday
from app.models.employee import Employee
from app.models.user import User, Role

client = TestClient(app)

from sqlalchemy import func
from sqlalchemy.orm import joinedload

@pytest.fixture(autouse=True)
def override_user():
    db = SessionLocal()
    admin_user = db.query(User).options(joinedload(User.role)).join(Role).filter(func.lower(Role.name).in_(["admin", "hr"])).first()
    if not admin_user:
        admin_role = db.query(Role).filter(func.lower(Role.name) == "admin").first()
        if not admin_role:
            admin_role = Role(name="Admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        admin_user = User(
            email="admin_test_delete@hrms.com",
            password_hash="testhash",
            display_name="Admin Test",
            role_id=admin_role.id,
            status="Active"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    db.close()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield
    app.dependency_overrides.clear()

from datetime import date

def test_delete_holiday_standalone():
    db = SessionLocal()
    target_date = date(2029, 11, 23)
    # Delete any previous test holiday if exists
    existing = db.query(Holiday).filter(Holiday.holiday_date == target_date).first()
    if existing:
        db.delete(existing)
        db.commit()

    test_h = Holiday(
        name="Test Delete Holiday",
        holiday_date=target_date,
        description="To be deleted",
        is_active=True
    )
    db.add(test_h)
    db.commit()
    db.refresh(test_h)
    h_id = test_h.id
    db.close()
    
    res = client.delete(f"/api/v1/master-data/holidays/{h_id}")
    assert res.status_code == 200
    assert res.json()["message"] == "Holiday deleted successfully"

    db = SessionLocal()
    deleted = db.query(Holiday).filter(Holiday.id == h_id).first()
    db.close()
    assert deleted is None

def test_delete_department_assigned_protection():
    db = SessionLocal()
    emp = db.query(Employee).filter(Employee.department != None).first()
    if emp and emp.department:
        dept = db.query(Department).filter(
            (Department.name == emp.department) | (Department.code == emp.department)
        ).first()
        if dept:
            res = client.delete(f"/api/v1/master-data/departments/{dept.id}")
            assert res.status_code == 400
            assert "Cannot delete department" in res.json()["detail"]
    db.close()
