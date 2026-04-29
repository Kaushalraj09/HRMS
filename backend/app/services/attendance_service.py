from sqlalchemy.orm import Session
from datetime import datetime, date
from app.models.attendance import Attendance
from app.models.employee import Employee

def get_today_record(db: Session, employee_id: int):
    today = date.today()
    return db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == today
    ).first()

def toggle_punch(db: Session, employee_id: int, work_mode: str):
    today_record = get_today_record(db, employee_id)
    now_time = datetime.now().time()

    if not today_record:
        # Create new record for today (Punch In)
        today_record = Attendance(
            employee_id=employee_id,
            date=date.today(),
            check_in=now_time,
            work_mode=work_mode,
            status="Checked In"
        )
        db.add(today_record)
    elif not today_record.check_out:
        # Update existing record (Punch Out)
        today_record.check_out = now_time
        today_record.status = "Checked Out"
        today_record.work_mode = work_mode
    else:
        # Already punched out, reset for a new check-in
        today_record.check_out = None
        today_record.check_in = now_time
        today_record.status = "Checked In"
        today_record.work_mode = work_mode

    db.commit()
    db.refresh(today_record)
    return today_record

def get_today_state(db: Session, employee_id: int):
    today_record = get_today_record(db, employee_id)
    if not today_record:
        return {
            "isPunchedIn": False,
            "status": "Not Marked",
            "checkIn": None,
            "checkOut": None,
            "workMode": "Office",
        }

    return {
        "isPunchedIn": bool(today_record.check_in and not today_record.check_out),
        "status": today_record.status,
        "checkIn": today_record.check_in,
        "checkOut": today_record.check_out,
        "workMode": today_record.work_mode or "Office",
    }

def get_my_history(db: Session, employee_id: int):
    return db.query(Attendance).filter(
        Attendance.employee_id == employee_id
    ).order_by(Attendance.date.desc()).all()

def list_all_attendance(db: Session, skip: int = 0, limit: int = 100):
    query = db.query(Attendance).join(Employee)
    
    total = query.count()
    records = query.offset(skip).limit(limit).all()
    
    formatted_data = []
    for record in records:
        employee_name = f"{record.employee.first_name} {record.employee.last_name}".strip()
        formatted_data.append({
            "id": record.id,
            "employeeName": employee_name,
            "employeeCode": record.employee.employee_code,
            "department": record.employee.department,
            "date": record.date,
            "checkIn": record.check_in,
            "checkOut": record.check_out,
            "status": record.status
        })
    
    return {"data": formatted_data, "total": total}
