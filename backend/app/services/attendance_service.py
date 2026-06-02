"""
Attendance Service - Manages single punch session attendance tracking.

This module implements a simplified single punch-in/punch-out system with:
- Single attendance record per day per employee
- Automatic break calculation for lunch spans
- Daily summary generation
- Location and image tracking (optional)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from app.models.attendance import Attendance, DailySummary
from app.models.timeoff import TimeOffRequest
from app.models.employee import Employee
from app.schemas.attendance import AttendanceResponse
from app.utils.employee_code import normalize_employee_code
from app.services.time_calculator import get_attendance_status

# Shift Configuration
TOTAL_SHIFT_WORKING_HOURS = 9.0  # 09:00 – 18:00
FIXED_BREAK_MINUTES = 60  # Fixed lunch break
REQUIRED_SHIFT_MINUTES = 540  # 9 hours = 540 minutes

SHIFT_START = time(9, 0)
SHIFT_END = time(18, 0)
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
SHIFT_TOTAL_SECONDS = int(TOTAL_SHIFT_WORKING_HOURS * 3600)


def calculate_attendance_metrics(attendance: Attendance) -> None:
    """
    Calculate working minutes, break, and overtime based on check_in and check_out times.
    
    Logic:
    - Total duration = check_out - check_in
    - Break = 60 min if span crosses lunch (13:00-14:00)
    - Working minutes = total duration - break
    - Overtime = working minutes beyond 480 min (8 hours)
    - Grand total = total duration (not working + overtime)
    
    Args:
        attendance: Attendance record to calculate metrics for
    """
    if attendance.punch_in and attendance.punch_out:
        rec_date = attendance.date or date.today()
        first_in = datetime.combine(rec_date, attendance.punch_in)
        last_out = datetime.combine(rec_date, attendance.punch_out)
        
        # Total session duration in minutes
        total_duration_seconds = int((last_out - first_in).total_seconds())
        total_duration_minutes = total_duration_seconds // 60
        
        # Calculate fixed lunch break when punch period spans lunch time
        break_minutes = 0
        if attendance.punch_in < time(13, 0) and attendance.punch_out > time(14, 0):
            break_minutes = FIXED_BREAK_MINUTES
        
        # Working minutes = total duration minus break
        working_minutes = max(0, total_duration_minutes - break_minutes)
        
        # Overtime = working minutes beyond 8 hours (480 minutes)
        overtime_minutes = max(0, working_minutes - 480)
        
        # Grand total = total session duration (not working + overtime separately)
        attendance.break_minutes = break_minutes
        attendance.total_working_minutes = working_minutes
        attendance.overtime_minutes = overtime_minutes
        attendance.grand_total_minutes = total_duration_minutes
    else:
        # No punch data available
        attendance.break_minutes = 0
        attendance.total_working_minutes = 0
        attendance.overtime_minutes = 0
        attendance.grand_total_minutes = 0




def _shift_elapsed_seconds(now: datetime | None = None) -> int:
    """
    Calculate elapsed seconds in shift from start to current time.
    
    Args:
        now: Current datetime (default: now in APP_TIMEZONE)
        
    Returns:
        int: Seconds elapsed in shift, capped at shift total
    """
    current = now or datetime.now(APP_TIMEZONE)
    current_seconds = current.hour * 3600 + current.minute * 60 + current.second
    shift_start_seconds = SHIFT_START.hour * 3600 + SHIFT_START.minute * 60
    shift_end_seconds = SHIFT_END.hour * 3600 + SHIFT_END.minute * 60

    if current_seconds <= shift_start_seconds:
        return 0
    if current_seconds >= shift_end_seconds:
        return SHIFT_TOTAL_SECONDS
    return current_seconds - shift_start_seconds


def get_timeoff_duration_for_date(db: Session, employee_id: int, target_date: date) -> float:
    """
    Get approved time-off duration for a specific date.
    
    Args:
        db: Database session
        employee_id: Employee to check
        target_date: Date to check
        
    Returns:
        float: Approved time-off hours
    """
    # Time-off queries are commented out for future work
    # total = (
    #     db.query(func.coalesce(func.sum(TimeOffRequest.duration_hours), 0.0))
    #     .filter(
    #         TimeOffRequest.employee_id == employee_id,
    #         TimeOffRequest.date == target_date,
    #         TimeOffRequest.status.in_(["Approved", "Active", "Completed"]),
    #     )
    #     .scalar()
    # )
    # return float(total or 0.0)
    return 0.0


def get_timeoff_duration_today(db: Session, employee_id: int) -> float:
    """
    Get approved time-off duration for today.
    
    Args:
        db: Database session
        employee_id: Employee to check
        
    Returns:
        float: Approved time-off hours for today
    """
    today = datetime.now(APP_TIMEZONE).date()
    return get_timeoff_duration_for_date(db, employee_id, today)


def upsert_daily_summary(db: Session, employee_id: int, target_date: date | None = None) -> DailySummary:
    """
    Generate or update daily summary for an employee.
    
    Calculates:
    - Total worked hours
    - Overtime minutes
    - Late arrival minutes
    - Early leave minutes
    
    Args:
        db: Database session
        employee_id: Employee to summarize
        target_date: Date to summarize (default: today)
        
    Returns:
        DailySummary: Generated summary record
    """
    summary_date = target_date or datetime.now(APP_TIMEZONE).date()
    
    # Get attendance record for the day
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == summary_date)
        .first()
    )
    
    if not attendance or not attendance.punch_in or not attendance.punch_out:
        # No complete punch data for the day
        return None
    
    # Calculate duration from punch_in to punch_out
    check_in_dt = datetime.combine(summary_date, attendance.punch_in)
    check_out_dt = datetime.combine(summary_date, attendance.punch_out)
    total_seconds = int((check_out_dt - check_in_dt).total_seconds())
    total_minutes = total_seconds // 60
    
    # Calculate late arrival
    late_minutes = 0
    check_in_minutes = attendance.punch_in.hour * 60 + attendance.punch_in.minute
    shift_start_minutes = SHIFT_START.hour * 60 + SHIFT_START.minute
    if check_in_minutes > shift_start_minutes:
        late_minutes = check_in_minutes - shift_start_minutes
    
    # Calculate early leave
    early_leave = 0
    check_out_minutes = attendance.punch_out.hour * 60 + attendance.punch_out.minute
    shift_end_minutes = SHIFT_END.hour * 60 + SHIFT_END.minute
    if check_out_minutes < shift_end_minutes:
        early_leave = shift_end_minutes - check_out_minutes
    
    # Calculate overtime
    overtime = max(0, total_minutes - int(TOTAL_SHIFT_WORKING_HOURS * 60))
    
    # Get or create summary record
    summary = (
        db.query(DailySummary)
        .filter(DailySummary.employee_id == employee_id, DailySummary.date == summary_date)
        .first()
    )
    
    if not summary:
        summary = DailySummary(employee_id=employee_id, date=summary_date)
        db.add(summary)
    
    # Update summary fields
    summary.total_worked_hours = round(total_seconds / 3600, 4)
    summary.overtime = overtime
    summary.late_minutes = late_minutes
    summary.early_leave = early_leave
    
    db.commit()
    db.refresh(summary)
    
    return summary


def punch_in(
    db: Session,
    employee_id: int,
    work_mode: str,
    latitude: float = None,
    longitude: float = None,
    address: str = None,
    image: str = None,
    custom_time: datetime = None,
) -> AttendanceResponse:
    """
    Punch in for the day. Single punch-in per day.
    
    Logic:
    - Get or create attendance record for today
    - If already punched in (is_working=1), raise error
    - Set check_in time with optional location/image
    - Mark as working
    
    Args:
        db: Database session
        employee_id: Employee to punch in
        work_mode: Office/Remote/Hybrid
        latitude: Optional check-in latitude
        longitude: Optional check-in longitude
        address: Optional check-in address
        image: Optional base64 check-in image
        custom_time: Optional custom time for testing
        
    Returns:
        AttendanceResponse: Updated attendance record
    """
    # Determine current time
    if custom_time:
        if custom_time.tzinfo is None:
            current = custom_time.replace(tzinfo=APP_TIMEZONE)
        else:
            current = custom_time.astimezone(APP_TIMEZONE)
    else:
        current = datetime.now(APP_TIMEZONE)
    
    today = current.date()
    
    # Get or create attendance for today
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == today)
        .first()
    )
    
    # Prevent duplicate punch-in
    if attendance:
        # Fetch employee information for extra detail fields
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        emp_code = employee.employee_code if employee else f"EMP-{employee_id:04d}"
        
        if attendance.is_working:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Already punched in. Please punch out first.",
                    "code": "ALREADY_PUNCHED_IN",
                    "employeeId": emp_code,
                    "punchInTiming": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                    "punchInAddress": attendance.punch_in_address,
                    "workMode": attendance.work_mode,
                },
            )
        if attendance.punch_out is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Already completed attendance for today. Multiple punches not allowed.",
                    "code": "ALREADY_PUNCHED_OUT",
                    "employeeId": emp_code,
                    "punchInTiming": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                    "punchOutTiming": attendance.punch_out.strftime("%I:%M %p") if attendance.punch_out else None,
                    "punchOutAddress": attendance.punch_out_address,
                    "workMode": attendance.work_mode,
                },
            )
    
    # Create new attendance if doesn't exist
    if not attendance:
        attendance = Attendance(
            employee_id=employee_id,
            date=today,
            is_working=1,
            work_mode=work_mode,
            status="Working",
        )
        db.add(attendance)
        db.flush()
    else:
        # Update existing attendance record
        attendance.is_working = 1
        attendance.work_mode = work_mode
        attendance.status = "Working"
    
    # Set punch-in with location and image (first check-in of the day)
    attendance.punch_in = current.time()
    attendance.punch_in_latitude = latitude
    attendance.punch_in_longitude = longitude
    attendance.punch_in_address = address
    attendance.punch_in_image = image
    
    db.commit()
    db.refresh(attendance)
    
    return to_attendance_response(attendance)

def punch_out(
    db: Session,
    employee_id: int,
    work_mode: str,
    latitude: float = None,
    longitude: float = None,
    address: str = None,
    image: str = None,
    custom_time: datetime = None,
) -> AttendanceResponse:
    """
    Punch out for the day. Single punch-out per day.
    
    Logic:
    - Get attendance for today
    - If no attendance found, raise error
    - If already punched out, raise error
    - If not working, raise error
    - Set check_out time with optional location/image
    - Calculate attendance metrics
    - Mark as not working
    - Generate daily summary
    
    Args:
        db: Database session
        employee_id: Employee to punch out
        work_mode: Office/Remote/Hybrid
        latitude: Optional check-out latitude
        longitude: Optional check-out longitude
        address: Optional check-out address
        image: Optional base64 check-out image
        custom_time: Optional custom time for testing
        
    Returns:
        AttendanceResponse: Updated attendance record
    """
    # Determine current time
    if custom_time:
        if custom_time.tzinfo is None:
            current = custom_time.replace(tzinfo=APP_TIMEZONE)
        else:
            current = custom_time.astimezone(APP_TIMEZONE)
    else:
        current = datetime.now(APP_TIMEZONE)
    
    today = current.date()
    
    # Get attendance for today
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == today)
        .first()
    )
    
    # Validate punch-out conditions
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "No attendance found for today. Please punch in first.",
                "code": "NO_ATTENDANCE_RECORD",
            },
        )
    
    if attendance.punch_out is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Already punched out. Multiple punch-outs not allowed.",
                "code": "ALREADY_PUNCHED_OUT",
                "checkIn": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                "checkOut": attendance.punch_out.strftime("%I:%M %p") if attendance.punch_out else None,
                "address": attendance.punch_out_address,
                "workMode": attendance.work_mode,
            },
        )
    
    if not attendance.is_working:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Not working. Cannot punch out.",
                "code": "NOT_WORKING",
                "checkIn": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                "workMode": attendance.work_mode,
            },
        )
    
    # Set punch-out with location and image
    attendance.punch_out = current.time()
    attendance.punch_out_latitude = latitude
    attendance.punch_out_longitude = longitude
    attendance.punch_out_address = address
    attendance.punch_out_image = image
    attendance.is_working = 0
    attendance.status = "Present"
    
    # Calculate metrics
    calculate_attendance_metrics(attendance)
    
    db.commit()
    db.refresh(attendance)
    
    # Generate daily summary
    upsert_daily_summary(db, employee_id, today)
    
    return to_attendance_response(attendance)

def get_today_state(db: Session, employee_id: int) -> dict:
    """
    Get current attendance state for today.
    
    Calculates:
    - Total worked seconds (including active session if still working)
    - Approved/time-off seconds
    - Remaining seconds = shift total - worked - approved
    - Current shift elapsed time
    
    Args:
        db: Database session
        employee_id: Employee to get state for
        
    Returns:
        dict: Attendance state with working metrics
    """
    current = datetime.now(APP_TIMEZONE)
    today = current.date()
    
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == today)
        .first()
    )
    
    if not attendance:
        # Automatically register that the employee has logged in today by creating a pre-punch record
        attendance = Attendance(
            employee_id=employee_id,
            date=today,
            is_working=0,
            work_mode="Office",
            status=get_attendance_status(None, None, today, current),
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        
    # Calculate total worked seconds
    worked_seconds = 0
    if attendance and attendance.punch_in and attendance.punch_out:
        # Full session completed
        check_in_dt = datetime.combine(today, attendance.punch_in, tzinfo=APP_TIMEZONE)
        check_out_dt = datetime.combine(today, attendance.punch_out, tzinfo=APP_TIMEZONE)
        worked_seconds = int((check_out_dt - check_in_dt).total_seconds())
    elif attendance and attendance.punch_in and attendance.is_working:
        # Active session - calculate time from check_in to now
        check_in_dt = datetime.combine(today, attendance.punch_in, tzinfo=APP_TIMEZONE)
        worked_seconds = int((current - check_in_dt).total_seconds())
    
    # Get approved time-off hours
    approved_hours = get_timeoff_duration_today(db, employee_id)
    approved_seconds = int(round(approved_hours * 3600))
    
    # Calculate remaining seconds = shift total - worked - approved
    remaining_seconds = max(0, SHIFT_TOTAL_SECONDS - worked_seconds - approved_seconds)
    
    # Calculate shift elapsed time
    shift_elapsed_seconds = _shift_elapsed_seconds(current)
    
    # Prepare response
    return {
        "employeeId": employee_id,
        "isWorking": bool(attendance and attendance.is_working),
        "status": get_attendance_status(attendance.punch_in, attendance.punch_out, attendance.date, current),
        "totalWorkedSeconds": worked_seconds,
        "approvedSeconds": approved_seconds,
        "remainingSeconds": remaining_seconds,
        "shiftTotalSeconds": SHIFT_TOTAL_SECONDS,
        "shiftElapsedSeconds": shift_elapsed_seconds,
        "shiftStart": SHIFT_START.strftime("%I:%M %p"),
        "shiftEnd": SHIFT_END.strftime("%I:%M %p"),
        "workMode": attendance.work_mode if attendance else "Office",
        "punchIn": attendance.punch_in if attendance else None,
        "punchOut": attendance.punch_out if attendance else None,
        "punchInLatitude": attendance.punch_in_latitude if attendance else None,
        "punchInLongitude": attendance.punch_in_longitude if attendance else None,
        "punchInAddress": attendance.punch_in_address if attendance else None,
        "punchOutLatitude": attendance.punch_out_latitude if attendance else None,
        "punchOutLongitude": attendance.punch_out_longitude if attendance else None,
        "punchOutAddress": attendance.punch_out_address if attendance else None,
        "punchInImage": attendance.punch_in_image if attendance else None,
        "punchOutImage": attendance.punch_out_image if attendance else None,
    }

def get_my_history(db: Session, employee_id: int) -> list[Attendance]:
    """
    Get attendance history for employee up to today.
    
    Args:
        db: Database session
        employee_id: Employee to get history for
        
    Returns:
        list[Attendance]: List of attendance records in descending date order
    """
    today = datetime.now(APP_TIMEZONE).date()
    return (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date <= today,
        )
        .order_by(Attendance.date.desc())
        .all()
    )


def to_attendance_response(record: Attendance) -> AttendanceResponse:
    """
    Convert attendance record to response schema.
    
    Automatically calculates all metrics and properly serializes
    all fields including optional location and image data.
    
    Args:
        record: Attendance database record
        
    Returns:
        AttendanceResponse: Properly formatted API response
    """
    calculate_attendance_metrics(record)
    
    # Calculate late minutes if punched in
    late_minutes = 0
    if record.punch_in:
        check_in_minutes = record.punch_in.hour * 60 + record.punch_in.minute
        shift_start_minutes = SHIFT_START.hour * 60 + SHIFT_START.minute
        if check_in_minutes > shift_start_minutes:
            late_minutes = check_in_minutes - shift_start_minutes
    
    return AttendanceResponse(
        id=record.id,
        employee_id=record.employee_id,
        date=record.date,
        scheduled_start=record.scheduled_start,
        scheduled_end=record.scheduled_end,
        task_description=record.task_description,
        punch_in=record.punch_in,
        punch_out=record.punch_out,
        status=get_attendance_status(record.punch_in, record.punch_out, record.date),
        work_mode=record.work_mode or "Office",
        total_working_minutes=record.total_working_minutes or 0,
        overtime_minutes=record.overtime_minutes or 0,
        break_minutes=record.break_minutes or 0,
        grand_total_minutes=record.grand_total_minutes or 0,
        late_minutes=late_minutes,
        punch_in_latitude=record.punch_in_latitude,
        punch_in_longitude=record.punch_in_longitude,
        punch_in_address=record.punch_in_address,
        punch_in_image=record.punch_in_image,
        punch_out_latitude=record.punch_out_latitude,
        punch_out_longitude=record.punch_out_longitude,
        punch_out_address=record.punch_out_address,
        punch_out_image=record.punch_out_image,
    )

def add_schedule(
    db: Session,
    employee_id: int,
    schedule_date: date,
    start_time: time,
    end_time: time,
    work_mode: str,
    task_description: str = None,
) -> AttendanceResponse:
    """
    Schedule a future shift for employee.
    
    Args:
        db: Database session
        employee_id: Employee to schedule
        schedule_date: Date to schedule
        start_time: Scheduled start time
        end_time: Scheduled end time
        work_mode: Office/Remote/Hybrid
        task_description: Optional task description
        
    Returns:
        AttendanceResponse: Scheduled attendance record
    """
    if schedule_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule attendance for past dates.",
        )
    
    record = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date == schedule_date,
        )
        .first()
    )
    
    if not record:
        record = Attendance(
            employee_id=employee_id,
            date=schedule_date,
            scheduled_start=start_time,
            scheduled_end=end_time,
            work_mode=work_mode,
            task_description=task_description,
            status="Not Marked",
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
    
    return to_attendance_response(record)

def list_all_attendance(db: Session, skip: int = 0, limit: int = 1000) -> dict:
    """
    List all attendance records (HR/Admin only).
    
    Args:
        db: Database session
        skip: Records to skip (pagination)
        limit: Records to return (pagination)
        
    Returns:
        dict: Paginated list of attendance records with total count
    """
    today = datetime.now(APP_TIMEZONE).date()
    query = (
        db.query(Attendance)
        .join(Employee)
        .filter(Attendance.date <= today)
        .order_by(Attendance.date.desc(), Attendance.punch_in.desc().nulls_last(), Attendance.id.desc())
    )
    
    total = query.count()
    records = query.offset(skip).limit(limit).all()
    
    formatted_data = []
    for record in records:
        calculate_attendance_metrics(record)
        employee_name = f"{record.employee.first_name} {record.employee.last_name}".strip() if record.employee else "Unknown Employee"
        
        # Calculate late minutes
        late_minutes = 0
        if record.punch_in:
            check_in_minutes = record.punch_in.hour * 60 + record.punch_in.minute
            shift_start_minutes = SHIFT_START.hour * 60 + SHIFT_START.minute
            if check_in_minutes > shift_start_minutes:
                late_minutes = check_in_minutes - shift_start_minutes
        
        formatted_data.append({
            "id": record.id,
            "employeeName": employee_name,
            "employeeCode": normalize_employee_code(record.employee.employee_code) if record.employee else "N/A",
            "department": (record.employee.department or "Unassigned") if record.employee else "Unassigned",
            "date": record.date,
            "scheduledStart": record.scheduled_start,
            "scheduledEnd": record.scheduled_end,
            "taskDescription": record.task_description,
            "punchIn": record.punch_in,
            "punchOut": record.punch_out,
            "status": get_attendance_status(record.punch_in, record.punch_out, record.date),
            "totalWorkingMinutes": record.total_working_minutes or 0,
            "overtimeMinutes": record.overtime_minutes or 0,
            "breakMinutes": record.break_minutes or 0,
            "grandTotalMinutes": record.grand_total_minutes or 0,
            "lateMinutes": late_minutes,
            "workMode": record.work_mode,
            "punchInAddress": record.punch_in_address,
            "punchOutAddress": record.punch_out_address,
            "punchInImage": record.punch_in_image,
            "punchOutImage": record.punch_out_image,
        })
    
    return {"data": formatted_data, "total": total}


def update_today_work_mode(
    db: Session,
    employee_id: int,
    work_mode: str,
) -> dict:
    """
    Update the work mode of today's attendance record.
    If the record does not exist yet, a pre-punch record is created.
    """
    current = datetime.now(APP_TIMEZONE)
    today = current.date()
    
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == today)
        .first()
    )
    
    if not attendance:
        # Create a pre-punch attendance record with the chosen work mode
        attendance = Attendance(
            employee_id=employee_id,
            date=today,
            is_working=0,
            work_mode=work_mode,
            status=get_attendance_status(None, None, today, current),
        )
        db.add(attendance)
    else:
        # Update the existing record's work mode
        attendance.work_mode = work_mode
        
    db.commit()
    db.refresh(attendance)
    
    return get_today_state(db, employee_id)

