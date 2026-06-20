import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.attendance import Attendance, AttendanceRegularizationRequest
from app.models.timeoff import TimeOffRequest
from app.models.approval_log import ApprovalLog
from app.models.login_activity import LoginActivity
from app.services import report_service

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed basic roles
        role_admin = Role(name="admin")
        role_hr = Role(name="hr")
        role_emp = Role(name="employee")
        db.add_all([role_admin, role_hr, role_emp])
        db.commit()
        
        # Seed users
        admin_user = User(email="admin@example.com", password_hash="hash", display_name="Admin User", role_id=role_admin.id)
        hr_user = User(email="hr@example.com", password_hash="hash", display_name="HR User", role_id=role_hr.id)
        emp_user = User(email="emp@example.com", password_hash="hash", display_name="Employee User", role_id=role_emp.id)
        db.add_all([admin_user, hr_user, emp_user])
        db.commit()
        
        # Seed employees
        emp = Employee(
            user_id=emp_user.id,
            first_name="Jane",
            last_name="Doe",
            employee_code="EMP002",
            department="Engineering",
            designation="Software Engineer",
            official_email="emp@example.com",
            mobile="0987654321",
            status="Active",
            doj=date(2025, 1, 1),
            timeoff_balance_hours=80.0
        )
        db.add(emp)
        db.commit()
        
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_attendance_summary_report(db_session):
    emp = db_session.query(Employee).first()
    
    # Add attendance
    a1 = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 10),
        punch_in=time(9, 0),
        punch_out=time(18, 0),
        total_working_minutes=480,
        status="Present"
    )
    a2 = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 11),
        punch_in=time(9, 30), # Late
        punch_out=time(18, 0),
        total_working_minutes=450,
        status="Half-Day"
    )
    db_session.add_all([a1, a2])
    db_session.commit()
    
    report = report_service.get_attendance_summary_report(
        db_session,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20),
        page=1,
        limit=10
    )
    
    assert report["total"] == 1
    row = report["data"][0]
    assert row["employeeCode"] == "EMP-0002"  # normalized
    assert row["presentDays"] == 1
    assert row["halfDays"] == 1
    assert row["absentDays"] == 0
    assert row["totalWorkingMinutes"] == 930

def test_late_arrival_report(db_session):
    emp = db_session.query(Employee).first()
    
    a1 = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 10),
        punch_in=time(9, 30), # Late (scheduled start is 9:00 AM, grace is 9:15 AM)
        punch_out=time(18, 0),
        status="Present"
    )
    a2 = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 11),
        punch_in=time(9, 5), # Inside grace period
        punch_out=time(18, 0),
        status="Present"
    )
    db_session.add_all([a1, a2])
    db_session.commit()
    
    report = report_service.get_late_arrival_report(
        db_session,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20)
    )
    
    assert report["total"] == 1
    row = report["data"][0]
    assert row["lateMinutes"] == 30  # 9:30 - 9:00 = 30 mins

def test_missing_punch_report(db_session):
    emp = db_session.query(Employee).first()
    
    # Missed punch due to no punch out on a past day
    a1 = Attendance(
        employee_id=emp.id,
        date=date(2026, 6, 10),
        punch_in=time(9, 0),
        punch_out=None,
        status="WORKING"
    )
    db_session.add(a1)
    db_session.commit()
    
    report = report_service.get_missing_punch_report(
        db_session,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20)
    )
    
    assert report["total"] == 1
    row = report["data"][0]
    assert row["reason"] == "Missing Punch Out"

def test_leave_usage_report(db_session):
    emp = db_session.query(Employee).first()
    
    req = TimeOffRequest(
        employee_id=emp.id,
        date=date(2026, 6, 12),
        leave_type="Full-Day",
        duration_hours=8.0,
        status="Approved",
        reason="Vacation"
    )
    db_session.add(req)
    db_session.commit()
    
    report = report_service.get_leave_usage_report(
        db_session,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20)
    )
    
    assert report["total"] == 1
    row = report["data"][0]
    assert row["leaveType"] == "Full-Day"
    assert row["durationHours"] == 8.0

def test_hr_workload_report(db_session):
    hr_user = db_session.query(User).filter(User.email == "hr@example.com").first()
    emp = db_session.query(Employee).first()
    
    # HR user processes a leave request
    req = TimeOffRequest(
        employee_id=emp.id,
        date=date(2026, 6, 12),
        leave_type="Full-Day",
        duration_hours=8.0,
        status="Approved"
    )
    db_session.add(req)
    db_session.commit()
    
    log = ApprovalLog(
        timeoff_request_id=req.id,
        action_by_user_id=hr_user.id,
        action="APPROVED",
        comments="Approved by HR",
        created_at=datetime(2026, 6, 12, 10, 0)
    )
    db_session.add(log)
    db_session.commit()
    
    report = report_service.get_hr_workload_report(
        db_session,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20)
    )
    
    # We should have HR workload entries
    hr_row = next(r for r in report["data"] if r["hrName"] == "HR User")
    assert hr_row["processedTimeoff"] == 1
    assert hr_row["totalHandled"] == 1

def test_employee_status_report(db_session):
    report = report_service.get_employee_status_report(db_session)
    assert report["total"] == 1
    row = report["data"][0]
    assert row["employeeName"] == "Jane Doe"
    assert row["status"] == "Active"

def test_login_activity_report(db_session):
    emp = db_session.query(Employee).first()
    
    act = LoginActivity(
        user_id=emp.user_id,
        employee_id=emp.id,
        ip_address="127.0.0.1",
        browser="Chrome",
        device="Desktop",
        operating_system="Windows",
        status="Success",
        login_time=datetime(2026, 6, 12, 9, 0)
    )

    db_session.add(act)
    db_session.commit()
    
    report = report_service.get_login_activity_summary_report(db_session)
    assert report["total"] == 1
    row = report["data"][0]
    assert row["employeeName"] == "Jane Doe"
    assert row["browser"] == "Chrome"
