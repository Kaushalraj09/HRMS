from sqlalchemy.orm import Session
from datetime import date
from app.models.user import User
from app.models.hr_user import HrUser
from app.models.employee import Employee
from app.models.attendance import Attendance

def get_admin_dashboard_data(db: Session):
    
    total_hrs = db.query(HrUser).count()
    total_emps = db.query(Employee).count()
    active_users = db.query(User).filter(User.status == "Active").count()
    
    today = date.today()
    present_today = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status != "Not Marked"
    ).count()

    
    recent_hrs = db.query(HrUser).order_by(HrUser.created_at.desc()).limit(6).all()
    recent_emps = db.query(Employee).order_by(Employee.created_at.desc()).limit(6).all()

    return {
        "cards": [
            {"icon": "fas fa-user-shield", "label": "Total HR Users", "value": str(total_hrs)},
            {"icon": "fas fa-users", "label": "Total Employees", "value": str(total_emps)},
            {"icon": "fas fa-user-check", "label": "Active Accounts", "value": str(active_users)},
            {"icon": "fas fa-calendar-check", "label": "Present Today", "value": str(present_today)}
        ],
        "hrUsers": [
            {
                "primary": hr.full_name,
                "secondary": hr.email,
                "tertiary": f"{hr.department} · {hr.designation}",
                "status": hr.status
            } for hr in recent_hrs
        ],
        "employees": [
            {
                "primary": emp.full_name,
                "secondary": emp.official_email,
                "tertiary": f"{emp.department} · {emp.designation}",
                "status": emp.status
            } for emp in recent_emps
        ]
    }

def get_hr_dashboard_data(db: Session):
    today = date.today()
    
    # 1. Attendance Metrics
    total_emps = db.query(Employee).count()
    present = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "Present").count()
    checked_in = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "Checked In").count()
    checked_out = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "Checked Out").count()
    not_marked = total_emps - (present + checked_in + checked_out)

    # 2. Breakdowns
    office_count = db.query(Employee).filter(Employee.work_location == "Main Office").count()
    remote_count = total_emps - office_count
    
    male_count = db.query(Employee).filter(Employee.gender == "Male").count()
    female_count = db.query(Employee).filter(Employee.gender == "Female").count()

    # 3. Recent Attendance (Last 8 records)
    recent_records = db.query(Attendance).order_by(Attendance.date.desc()).limit(8).all()

    # 4. Format the response
    return {
        "totalEmployees": total_emps,
        "presentEmployees": present,
        "checkedInEmployees": checked_in,
        "checkedOutEmployees": checked_out,
        "notMarkedEmployees": not_marked,
        "workModeBreakdown": [remote_count, office_count],
        "genderBreakdown": [female_count, male_count],
        "quickStats": [
            {"total": db.query(HrUser).count(), "name": "HR Users"},
            {"total": 12, "name": "Departments"},
            {"total": db.query(Employee).filter(Employee.status == "Active").count(), "name": "Active Employees"}
        ],
        "recentTimeSheets": [
            {
                "employee": record.employee.full_name if record.employee else "Unknown",
                "date": record.date.strftime("%Y-%m-%d"),
                "punchIn": record.check_in.strftime("%H:%M") if record.check_in else "-",
                "punchOut": record.check_out.strftime("%H:%M") if record.check_out else "-",
                "breakTime": f"{record.break_minutes} mins",
                "overtime": f"{record.overtime_minutes} mins",
                "totalHours": "8h 0m",
                "status": record.status
            } for record in recent_records
        ]
    }

