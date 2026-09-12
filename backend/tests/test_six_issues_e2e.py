from datetime import date, time, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, SessionLocal
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.timeoff import TimeOffRequest
from app.models.master_data import LeaveType
from app.core.security import create_access_token
from app.services.timeoff_service import get_employee_leave_balances, approve_request


@pytest.fixture
def client():
    return TestClient(app)


def test_issue_6_multitab_auth_payload(client):
    """Issue 6: Login response must include accessToken in JSON body to support tab-scoped auth."""
    from app.core.security import hash_password
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "test_auth@hrms.com").first()
        if not user:
            role = db.query(Role).first()
            user = User(
                email="test_auth@hrms.com",
                password_hash=hash_password("password123"),
                display_name="Test Auth User",
                role_id=role.id if role else 1,
                status="Active"
            )
            db.add(user)
        else:
            user.password_hash = hash_password("password123")
        db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/auth/login", json={"email": "test_auth@hrms.com", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "accessToken" in data or "access_token" in data
    token = data.get("accessToken") or data.get("access_token")
    assert token is not None and len(token) > 20

    # Verify Bearer header works for protected endpoints
    res2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    assert res2.json()["email"] == "test_auth@hrms.com"


def test_issue_1_leave_balance_deduction_on_approval(client):
    """Issue 1: Leave balance is deducted ONLY when approved, not when pending or rejected, and is idempotent."""
    from app.domain.attendance.repositories.shift_repository import ShiftRepository
    from app.domain.attendance.services.shift_calculation_service import ShiftCalculationService
    from app.models.approval_log import ApprovalLog

    db: Session = SessionLocal()
    try:
        # Find or create a test employee
        emp = db.query(Employee).filter(Employee.status == "Active").first()
        assert emp is not None, "Active employee required"
        emp_id = emp.id

        shift = ShiftRepository.get_assigned_shift(db, emp_id, date.today())
        eff_shift = ShiftCalculationService.get_effective_shift(shift)
        shift_hours = float(eff_shift.working_hours or 8.0) or 8.0

        # Initial balance calculation
        initial_balances = get_employee_leave_balances(db, emp_id)
        assert "casual" in initial_balances
        initial_casual_avail = initial_balances["casual"]["availableDays"]

        # Create a pending leave request for a future weekday
        target_date = date.today() + timedelta(days=20)
        while target_date.weekday() >= 5:  # ensure weekday
            target_date += timedelta(days=1)

        req = TimeOffRequest(
            employee_id=emp_id,
            date=target_date,
            leave_type="Casual Leave",
            duration_hours=shift_hours,
            status="Pending",
            reason="E2E test leave"
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        # 1. While Pending, available balance reflects pending allocation (available = allocated - used - pending)
        pending_balances = get_employee_leave_balances(db, emp_id)
        assert pending_balances["casual"]["availableDays"] == initial_casual_avail - 1

        # 2. When Approved, balance MUST be deducted by 1 day
        approved_req = approve_request(db, req.id, action="APPROVE", admin_user_id=1, enforce_approval_stage=False)
        assert approved_req.status == "Approved"

        after_approve_balances = get_employee_leave_balances(db, emp_id)
        expected_avail = round(initial_casual_avail - 1.0, 1)
        assert after_approve_balances["casual"]["availableDays"] == expected_avail
        assert after_approve_balances["casual"]["usedDays"] == round(initial_balances["casual"]["usedDays"] + 1.0, 1)

        # 3. Calling approve again must be rejected (idempotency)
        with pytest.raises(Exception):
            approve_request(db, req.id, action="APPROVE", admin_user_id=1, enforce_approval_stage=False)

        # Clean up the test request
        db.query(ApprovalLog).filter(ApprovalLog.timeoff_request_id == req.id).delete()
        db.delete(req)
        db.commit()
    finally:
        db.close()


def test_issue_5_timeoff_in_attendance_response():
    """Issue 5: Attendance response includes timeoffMinutes and timeoffHours."""
    from app.services.attendance_service import to_attendance_response
    db: Session = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.status == "Active").first()
        att = db.query(Attendance).filter(Attendance.employee_id == emp.id).first()
        if not att:
            att = Attendance(
                employee_id=emp.id,
                date=date.today(),
                status="Present",
                total_working_minutes=480
            )
            db.add(att)
            db.commit()
            db.refresh(att)

        resp = to_attendance_response(att, db)
        assert hasattr(resp, "timeoff_minutes")
        assert hasattr(resp, "timeoff_hours")
        d = resp.model_dump(by_alias=True)
        assert "timeoffMinutes" in d
        assert "timeoffHours" in d
    finally:
        db.close()
