from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from app.models.attendance import Attendance, DailySummary
from app.models.timeoff import TimeOffRequest
from app.utils.employee_code import normalize_employee_code
from app.models.employee import Employee
from app.schemas.attendance import AttendanceResponse

TOTAL_SHIFT_WORKING_HOURS = 9.0  # 09:00–18:00
FIXED_BREAK_MINUTES = 60
REQUIRED_SHIFT_MINUTES = 540 # 9 hours including break

SHIFT_START = time(9, 0)
SHIFT_END = time(18, 0)
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
SHIFT_TOTAL_SECONDS = int(TOTAL_SHIFT_WORKING_HOURS * 3600)


def calculate_attendance_metrics(attendance: Attendance):
    """Dynamically calculates working minutes, overtime, break and grand total based on check_in/check_out."""
    if attendance.check_in and attendance.check_out:
        rec_date = attendance.date or date.today()
        first_in = datetime.combine(rec_date, attendance.check_in)
        last_out = datetime.combine(rec_date, attendance.check_out)
        total_duration_seconds = int((last_out - first_in).total_seconds())
        total_duration_minutes = total_duration_seconds // 60
        
        # Calculate lunch break minutes (60 mins if check_in before 1 PM and check_out after 2 PM)
        break_minutes = 0
        if attendance.check_in < time(13, 0) and attendance.check_out > time(14, 0):
            break_minutes = 60
            
        attendance.break_minutes = break_minutes
        attendance.total_working_minutes = max(0, total_duration_minutes - break_minutes)
        attendance.overtime_minutes = max(0, total_duration_minutes - REQUIRED_SHIFT_MINUTES)
        attendance.grand_total_minutes = attendance.total_working_minutes + attendance.overtime_minutes
    else:
        attendance.break_minutes = 0
        attendance.total_working_minutes = 0
        attendance.overtime_minutes = 0
        attendance.grand_total_minutes = 0


def _now() -> datetime:
    """Return the current business-local timestamp used for attendance rules."""
    return datetime.now(APP_TIMEZONE)


def _minutes_since_midnight(value: time | None) -> int:
    if not value:
        return 0
    return value.hour * 60 + value.minute


def _seconds_between(target_date: date, start: time, end: time) -> int:
    start_dt = datetime.combine(target_date, start)
    end_dt = datetime.combine(target_date, end)
    return max(0, int((end_dt - start_dt).total_seconds()))


def _shift_elapsed_seconds(now: datetime | None = None) -> int:
    current = now or _now()
    current_seconds = current.hour * 3600 + current.minute * 60 + current.second
    shift_start_seconds = SHIFT_START.hour * 3600 + SHIFT_START.minute * 60 + SHIFT_START.second
    shift_end_seconds = SHIFT_END.hour * 3600 + SHIFT_END.minute * 60 + SHIFT_END.second

    if current_seconds <= shift_start_seconds:
        return 0
    if current_seconds >= shift_end_seconds:
        return SHIFT_TOTAL_SECONDS
    return current_seconds - shift_start_seconds


def _closed_session_seconds(records: list[Attendance]) -> int:
    return sum(
        _seconds_between(record.date, record.check_in, record.check_out)
        for record in records
        if record.check_in and record.check_out
    )


def _get_today_records(db: Session, employee_id: int) -> list[Attendance]:
    today = _now().date()
    return (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == today)
        .order_by(Attendance.check_in.asc().nulls_last(), Attendance.id.asc())
        .all()
    )


def _get_open_session(db: Session, employee_id: int) -> Attendance | None:
    today = _now().date()
    return (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date == today,
            Attendance.check_in.isnot(None),
            Attendance.check_out.is_(None),
        )
        .order_by(Attendance.id.desc())
        .first()
    )


def get_today_record(db: Session, employee_id: int):
    today = _now().date()
    return db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == today
    ).first()

def get_timeoff_duration_for_date(db: Session, employee_id: int, target_date: date) -> float:
    total = (
        db.query(func.coalesce(func.sum(TimeOffRequest.duration_hours), 0.0))
        .filter(
            TimeOffRequest.employee_id == employee_id,
            TimeOffRequest.date == target_date,
            TimeOffRequest.status.in_(["Approved", "Active", "Completed"]),
        )
        .scalar()
    )
    return float(total or 0.0)


def get_timeoff_duration_today(db: Session, employee_id: int) -> float:
    return get_timeoff_duration_for_date(db, employee_id, _now().date())


def upsert_daily_summary(db: Session, employee_id: int, target_date: date | None = None) -> DailySummary:
    """Persist the daily attendance rollup for closed punch sessions."""
    summary_date = target_date or _now().date()
    records = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == summary_date)
        .order_by(Attendance.check_in.asc().nulls_last(), Attendance.id.asc())
        .all()
    )
    total_seconds = _closed_session_seconds(records)
    total_minutes = total_seconds // 60
    first_check_in = next((record.check_in for record in records if record.check_in), None)
    last_check_out = next((record.check_out for record in reversed(records) if record.check_out), None)

    late_minutes = 0
    if first_check_in and _minutes_since_midnight(first_check_in) > _minutes_since_midnight(SHIFT_START):
        late_minutes = _minutes_since_midnight(first_check_in) - _minutes_since_midnight(SHIFT_START)

    early_leave = 0
    if last_check_out and _minutes_since_midnight(last_check_out) < _minutes_since_midnight(SHIFT_END):
        early_leave = _minutes_since_midnight(SHIFT_END) - _minutes_since_midnight(last_check_out)

    overtime = max(0, total_minutes - int(TOTAL_SHIFT_WORKING_HOURS * 60))
    summary = (
        db.query(DailySummary)
        .filter(DailySummary.employee_id == employee_id, DailySummary.date == summary_date)
        .first()
    )
    if not summary:
        summary = DailySummary(employee_id=employee_id, date=summary_date)
        db.add(summary)

    summary.total_worked_hours = round(total_seconds / 3600, 4)
    summary.overtime = overtime
    summary.late_minutes = late_minutes
    summary.early_leave = early_leave
    return summary

from app.models.attendance import Attendance, DailySummary, PunchLog

def punch_in(db: Session, employee_id: int, work_mode: str, latitude: float = None, longitude: float = None, address: str = None, image: str = None):
    current = _now()
    today = current.date()
    
    attendance = get_today_record(db, employee_id)
    if attendance and attendance.check_in is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already punched in for today. Multiple punches are not allowed."
        )

    if not attendance:
        attendance = Attendance(
            employee_id=employee_id, 
            date=today, 
            is_working=1,
            work_mode=work_mode,
            status="Working"
        )
        db.add(attendance)
        db.flush()
    else:
        if attendance.is_working:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already marked as working."
            )
        attendance.is_working = 1
        attendance.work_mode = work_mode
        attendance.status = "Working"

    log = PunchLog(
        employee_id=employee_id,
        attendance_id=attendance.id,
        date=today,
        punch_in=current,
        work_mode=work_mode,
        latitude=latitude,
        longitude=longitude,
        address=address
    )
    
    # Set first check-in of the day
    if attendance.check_in is None:
        attendance.check_in = current.time()
        attendance.check_in_latitude = latitude
        attendance.check_in_longitude = longitude
        attendance.check_in_address = address
        attendance.check_in_image = image  # Stored once – never overwritten by punch-out

    db.add(log)
    db.commit()
    db.refresh(attendance)
    return attendance

def punch_out(db: Session, employee_id: int, work_mode: str, latitude: float = None, longitude: float = None, address: str = None, image: str = None):
    current = _now()
    today = current.date()
    
    attendance = get_today_record(db, employee_id)
    if attendance and attendance.check_out is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already punched out for today. Multiple punches are not allowed."
        )

    if not attendance or not attendance.is_working:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot punch out while not working."
        )

    log = db.query(PunchLog).filter(
        PunchLog.attendance_id == attendance.id,
        PunchLog.punch_out.is_(None)
    ).order_by(PunchLog.id.desc()).first()
    
    if log:
        log.punch_out = current
        log.latitude = latitude
        log.longitude = longitude
        log.address = address
        duration = int((log.punch_out - log.punch_in).total_seconds())
        log.duration_seconds = duration
        attendance.total_worked_seconds += duration

    # Set/Update last check-out of the day (check_in_image is intentionally NOT touched)
    attendance.check_out = current.time()
    attendance.check_out_latitude = latitude
    attendance.check_out_longitude = longitude
    attendance.check_out_address = address
    attendance.check_out_image = image  # Stored separately alongside check_in_image
    attendance.is_working = 0
    attendance.status = "Not Working"

    # Calculate Attendance Metrics using shared helper
    calculate_attendance_metrics(attendance)

    db.commit()
    db.refresh(attendance)
    return attendance

def get_today_state(db: Session, employee_id: int):
    current = _now()
    today = current.date()
    attendance = get_today_record(db, employee_id)
    
    worked_seconds = attendance.total_worked_seconds if attendance else 0
    is_working = bool(attendance.is_working) if attendance else False
    
    if is_working:
        log = db.query(PunchLog).filter(
            PunchLog.attendance_id == attendance.id,
            PunchLog.punch_out.is_(None)
        ).order_by(PunchLog.id.desc()).first()
        if log:
            active_seconds = int((current - log.punch_in).total_seconds())
            worked_seconds += active_seconds

    approved_hours = get_timeoff_duration_today(db, employee_id)
    approved_seconds = int(round(approved_hours * 3600))
    
    # Shift logic: Remaining = (Time until 6 PM) - Approved
    shift_elapsed_seconds = _shift_elapsed_seconds(current)
    seconds_until_shift_end = max(0, SHIFT_TOTAL_SECONDS - shift_elapsed_seconds)
    remaining_seconds = max(0, seconds_until_shift_end - approved_seconds)
    
    return {
        "isWorking": is_working,
        "status": "Working" if is_working else "Not Working",
        "totalWorkedSeconds": worked_seconds,
        "approvedSeconds": approved_seconds,
        "remainingSeconds": remaining_seconds,
        "shiftTotalSeconds": SHIFT_TOTAL_SECONDS,
        "shiftElapsedSeconds": shift_elapsed_seconds,
        "shiftStart": SHIFT_START.strftime("%I:%M %p"),
        "shiftEnd": SHIFT_END.strftime("%I:%M %p"),
        "workMode": attendance.work_mode if attendance else "Office",
        "checkIn": attendance.check_in if attendance else None,
        "checkOut": attendance.check_out if attendance else None,
        "checkInLatitude": attendance.check_in_latitude if attendance else None,
        "checkInLongitude": attendance.check_in_longitude if attendance else None,
        "checkInAddress": attendance.check_in_address if attendance else None,
        "checkOutLatitude": attendance.check_out_latitude if attendance else None,
        "checkOutLongitude": attendance.check_out_longitude if attendance else None,
        "checkOutAddress": attendance.check_out_address if attendance else None,
        "checkInImage": attendance.check_in_image if attendance else None,
        "checkOutImage": attendance.check_out_image if attendance else None,
    }

def get_my_history(db: Session, employee_id: int):
    today = _now().date()
    return (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date <= today
        )
        .order_by(Attendance.date.desc())
        .all()
    )


def to_attendance_response(record: Attendance) -> AttendanceResponse:
    """Expose attendance rows."""
    calculate_attendance_metrics(record)
    late_minutes = 0
    if record.check_in:
        check_in_min = record.check_in.hour * 60 + record.check_in.minute
        if check_in_min > 540:  # 9:00 AM in minutes
            late_minutes = check_in_min - 540

    return AttendanceResponse(
        id=record.id,
        date=record.date,
        scheduled_start=record.scheduled_start,
        scheduled_end=record.scheduled_end,
        task_description=record.task_description,
        check_in=record.check_in,
        check_out=record.check_out,
        status=record.status or "Not Marked",
        work_mode=record.work_mode or "Office",
        total_working_minutes=record.total_working_minutes or 0,
        overtime_minutes=record.overtime_minutes or 0,
        break_minutes=record.break_minutes or 0,
        grand_total_minutes=record.grand_total_minutes or 0,
        late_minutes=late_minutes
    )

def add_schedule(db: Session, employee_id: int, schedule_date: date, start_time, end_time, work_mode: str, task_description: str = None):
    if schedule_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule attendance for past dates.",
        )

    record = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == schedule_date
    ).first()
    
    if not record:
        record = Attendance(
            employee_id=employee_id,
            date=schedule_date,
            scheduled_start=start_time,
            scheduled_end=end_time,
            work_mode=work_mode,
            task_description=task_description,
            status="Not Marked"
        )
        db.add(record)
    else:
        record.scheduled_start = start_time
        record.scheduled_end = end_time
        if task_description is not None:
            record.task_description = task_description
        if work_mode:
            record.work_mode = work_mode
            
    db.commit()
    db.refresh(record)
    return record

def list_all_attendance(db: Session, skip: int = 0, limit: int = 1000):
    today = _now().date()
    query = (
        db.query(Attendance)
        .join(Employee)
        .filter(Attendance.date <= today)
        .order_by(Attendance.date.desc(), Attendance.check_in.desc().nulls_last(), Attendance.id.desc())
    )
    
    total = query.count()
    records = query.offset(skip).limit(limit).all()
    
    formatted_data = []
    for record in records:
        calculate_attendance_metrics(record)
        employee_name = f"{record.employee.first_name} {record.employee.last_name}".strip()
        late_minutes = 0
        if record.check_in:
            check_in_min = record.check_in.hour * 60 + record.check_in.minute
            if check_in_min > 540:  # 9:00 AM in minutes
                late_minutes = check_in_min - 540

        formatted_data.append({
            "id": record.id,
            "employeeName": employee_name,
            "employeeCode": normalize_employee_code(record.employee.employee_code),
            "department": record.employee.department,
            "date": record.date,
            "scheduledStart": record.scheduled_start,
            "scheduledEnd": record.scheduled_end,
            "taskDescription": record.task_description,
            "checkIn": record.check_in,
            "checkOut": record.check_out,
            "status": record.status or "Not Marked",
            "totalWorkingMinutes": record.total_working_minutes or 0,
            "overtimeMinutes": record.overtime_minutes or 0,
            "breakMinutes": record.break_minutes or 0,
            "grandTotalMinutes": record.grand_total_minutes or 0,
            "lateMinutes": late_minutes,
            "workMode": record.work_mode,
            "checkInAddress": record.check_in_address,
            "checkOutAddress": record.check_out_address
        })
    
    return {"data": formatted_data, "total": total}
