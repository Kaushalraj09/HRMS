from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.models.user import Role, User
from app.services.attendance_service import calculate_attendance_metrics


def _employee_query(db: Session):
    return (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name) == "employee")
    )


def get_admin_dashboard_data(db: Session):
    total_hrs = db.query(HrUser).count()
    # Count both HRs and Employees together as the total workforce employees
    total_emps = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name).in_(["employee", "hr"]))
        .count()
    )
    active_users = db.query(User).filter(User.status == "Active").count()

    today = date.today()
    present_today = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status != "Not Marked"
    ).count()

    recent_hrs = db.query(HrUser).order_by(HrUser.created_at.desc()).limit(6).all()
    # Fetch recent employees including both HRs and Employees for admin dashboard
    recent_emps = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name).in_(["employee", "hr"]))
        .order_by(Employee.created_at.desc())
        .limit(6)
        .all()
    )

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
                "primary": f"{emp.first_name} {emp.last_name}".strip(),
                "secondary": emp.official_email,
                "tertiary": f"{emp.department} · {emp.designation}",
                "status": emp.status
            } for emp in recent_emps
        ]
    }


def get_hr_dashboard_data(db: Session):
    today = date.today()

    total_emps = _employee_query(db).count()
    present = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "Present").count()
    checked_in = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "Checked In").count()
    checked_out = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "Checked Out").count()
    not_marked = total_emps - (present + checked_in + checked_out)

    office_count = _employee_query(db).filter(Employee.work_location == "Main Office").count()
    remote_count = total_emps - office_count

    male_count = _employee_query(db).filter(Employee.gender == "Male").count()
    female_count = _employee_query(db).filter(Employee.gender == "Female").count()

    recent_records = (
        db.query(Attendance)
        .filter(Attendance.date <= today)
        .order_by(Attendance.date.desc(), Attendance.check_in.desc().nulls_last(), Attendance.id.desc())
        .limit(8)
        .all()
    )
    for record in recent_records:
        calculate_attendance_metrics(record)

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
            {"total": _employee_query(db).filter(Employee.status == "Active").count(), "name": "Active Employees"}
        ],
        "recentTimeSheets": [
            {
                "employee": f"{record.employee.first_name} {record.employee.last_name}".strip() if record.employee else "Unknown",
                "employeeCode": record.employee.employee_code if record.employee else "N/A",
                "date": record.date.strftime("%Y-%m-%d"),
                "punchIn": record.check_in.strftime("%H:%M") if record.check_in else "-",
                "punchOut": record.check_out.strftime("%H:%M") if record.check_out else "-",
                "breakTime": f"{record.break_minutes or 0} mins",
                "overtime": f"{record.overtime_minutes or 0} mins",
                "totalHours": f"{record.total_working_minutes // 60}h {record.total_working_minutes % 60}m" if record.total_working_minutes else "0h 0m",
                "status": record.status,
                "checkInImage": record.check_in_image,
                "checkOutImage": record.check_out_image
            } for record in recent_records
        ]
    }
