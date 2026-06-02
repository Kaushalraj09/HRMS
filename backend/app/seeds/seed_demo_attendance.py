from datetime import date, time, timedelta
from sqlalchemy.orm import Session
from app.models.attendance import Attendance, DailySummary
from app.models.employee import Employee


def seed_attendance(db: Session):
    employee = db.query(Employee).filter(Employee.official_email == "emp@hrms.com").first()
    if not employee:
        print("Demo employee not found. Skipping attendance seed.")
        return

    # Skip seeding if the employee already has attendance records to preserve their actual/testing history
    existing_count = db.query(Attendance).filter(Attendance.employee_id == employee.id).count()
    if existing_count > 0:
        print("Demo employee already has attendance records. Skipping seeding to preserve history.")
        return

    base_date = date.today() - timedelta(days=1)
    demo_rows = [
        {
            "date": base_date,
            "punch_in": time(9, 30),
            "punch_out": time(18, 0),
            "break_minutes": 45,
            "overtime_minutes": 15,
            "work_mode": "Office",
            "status": "Present",
        },
        {
            "date": base_date - timedelta(days=1),
            "punch_in": time(9, 35),
            "punch_out": time(18, 10),
            "break_minutes": 30,
            "overtime_minutes": 10,
            "work_mode": "Remote",
            "status": "Present",
        },
        {
            "date": base_date - timedelta(days=2),
            "punch_in": time(9, 40),
            "punch_out": None,
            "break_minutes": 0,
            "overtime_minutes": 0,
            "work_mode": "Office",
            "status": "Working",
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

        existing.punch_in = row["punch_in"]
        existing.punch_out = row["punch_out"]
        existing.break_minutes = row["break_minutes"]
        existing.overtime_minutes = row["overtime_minutes"]
        existing.work_mode = row["work_mode"]
        existing.status = row["status"]

    db.commit()
