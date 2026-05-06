from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.employee import Employee


def seed_attendance(db: Session):
    employee = db.query(Employee).filter(Employee.official_email == "emp@hrms.com").first()
    if not employee:
        print("Demo employee not found. Skipping attendance seed.")
        return

    base_date = date.today()
    demo_rows = [
        {
            "date": base_date,
            "check_in": time(9, 30),
            "check_out": time(18, 0),
            "break_minutes": 45,
            "overtime_minutes": 15,
            "work_mode": "Office",
            "status": "Present",
        },
        {
            "date": base_date - timedelta(days=1),
            "check_in": time(9, 35),
            "check_out": time(18, 10),
            "break_minutes": 30,
            "overtime_minutes": 10,
            "work_mode": "Remote",
            "status": "Present",
        },
        {
            "date": base_date - timedelta(days=2),
            "check_in": time(9, 40),
            "check_out": None,
            "break_minutes": 0,
            "overtime_minutes": 0,
            "work_mode": "Office",
            "status": "Checked In",
        },
    ]

    for row in demo_rows:
        existing = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id == employee.id,
                Attendance.date == row["date"],
            )
            .first()
        )

        if not existing:
            existing = Attendance(employee_id=employee.id, date=row["date"])
            db.add(existing)

        existing.check_in = row["check_in"]
        existing.check_out = row["check_out"]
        existing.break_minutes = row["break_minutes"]
        existing.overtime_minutes = row["overtime_minutes"]
        existing.work_mode = row["work_mode"]
        existing.status = row["status"]

    db.commit()
