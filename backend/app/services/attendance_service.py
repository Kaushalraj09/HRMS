"""
Attendance Service - Manages single punch session attendance tracking.

This module implements a simplified single punch-in/punch-out system with:
- Single attendance record per day per employee
- Automatic break calculation for lunch spans
- Daily summary generation
- Location and image tracking (optional)
"""

from sqlalchemy.orm import Session
from sqlalchemy import literal, or_, func
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from app.models.attendance import Attendance
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
    Calculate working minutes, break, overtime, and grand total based on check_in and check_out times.
    Uses the new enterprise rules from time_calculator.
    """
    from app.services.time_calculator import calculate_times
    calculate_times(attendance)




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

def _normalize_attendance_status(status: str) -> str:
    known_statuses = {
        "present": "Present",
        "working": "Working",
        "absent": "Absent",
        "not marked": "Not Marked",
        "notmarked": "Not Marked",
        "punched in": "Working",
        "punched out": "Present",
        "not working": "Present",
    }
    value = (status or "").strip().lower()
    return known_statuses.get(value, status or "")


def _matches_computed_status(record: Attendance, status_filter: str) -> bool:
    if not status_filter:
        return True
    requested = _normalize_attendance_status(status_filter).lower()
    actual = get_attendance_status(record.punch_in, record.punch_out, record.date).lower()
    return actual == requested or requested in actual


def _attendance_metrics(records: list[Attendance]) -> dict:
    metrics = {
        "present": 0,
        "working": 0,
        "absent": 0,
        "notMarked": 0,
    }
    for record in records:
        status_value = get_attendance_status(record.punch_in, record.punch_out, record.date)
        if status_value == "Present":
            metrics["present"] += 1
        elif status_value == "Working":
            metrics["working"] += 1
        elif status_value == "Absent":
            metrics["absent"] += 1
        elif status_value == "Not Marked":
            metrics["notMarked"] += 1
    return metrics


def get_my_history(
    db: Session,
    employee_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
    status_filter: str = "",
) -> list[Attendance]:
    """
    Get attendance history for employee up to today.
    
    Args:
        db: Database session
        employee_id: Employee to get history for
        
    Returns:
        list[Attendance]: List of attendance records in descending date order
    """
    today = datetime.now(APP_TIMEZONE).date()
    query = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date <= today,
        )
    )

    if from_date:
        query = query.filter(Attendance.date >= from_date)
    if to_date:
        query = query.filter(Attendance.date <= to_date)

    records = query.order_by(
        Attendance.date.desc(),
        Attendance.punch_in.desc().nulls_last(),
        Attendance.id.desc(),
    ).all()
    return [record for record in records if _matches_computed_status(record, status_filter)]


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
    
    # Calculate late minutes and early exit minutes
    from app.services.time_calculator import calculate_late_minutes, calculate_early_exit_minutes
    late_minutes = calculate_late_minutes(record.punch_in)
    early_exit_minutes = calculate_early_exit_minutes(record.punch_out)
    
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
        early_exit_minutes=early_exit_minutes,
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

def list_all_attendance(
    db: Session,
    page: int = 1,
    limit: int = 10,
    from_date: date | None = None,
    to_date: date | None = None,
    search: str = "",
    department: str = "",
    status_filter: str = "",
    location: str = "",
) -> dict:
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
    )

    if from_date:
        query = query.filter(Attendance.date >= from_date)
    if to_date:
        query = query.filter(Attendance.date <= to_date)
    if department:
        query = query.filter(Employee.department == department)
    if location:
        query = query.filter(Attendance.work_mode == location)

    search_value = (search or "").strip()
    if search_value:
        like_value = f"%{search_value}%"
        full_name = func.coalesce(Employee.first_name, "") + literal(" ") + func.coalesce(Employee.last_name, "")
        query = query.filter(
            or_(
                Employee.first_name.ilike(like_value),
                Employee.last_name.ilike(like_value),
                full_name.ilike(like_value),
                Employee.employee_code.ilike(like_value),
            )
        )
    
    records = query.order_by(
        Attendance.date.desc(),
        Attendance.punch_in.desc().nulls_last(),
        Attendance.id.desc(),
    ).all()
    records = [record for record in records if _matches_computed_status(record, status_filter)]
    total = len(records)
    metrics = _attendance_metrics(records)
    start = (page - 1) * limit
    paged_records = records[start : start + limit]
    
    formatted_data = []
    for record in paged_records:
        calculate_attendance_metrics(record)
        employee_name = f"{record.employee.first_name} {record.employee.last_name}".strip() if record.employee else "Unknown Employee"
        
        # Calculate late minutes and early exit minutes
        from app.services.time_calculator import calculate_late_minutes, calculate_early_exit_minutes
        late_minutes = calculate_late_minutes(record.punch_in)
        early_exit_minutes = calculate_early_exit_minutes(record.punch_out)
        
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
            "earlyExitMinutes": early_exit_minutes,
            "workMode": record.work_mode,
            "punchInAddress": record.punch_in_address,
            "punchOutAddress": record.punch_out_address,
            "punchInImage": record.punch_in_image,
            "punchOutImage": record.punch_out_image,
        })
    
    return {"data": formatted_data, "total": total, "metrics": metrics}


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


def get_employee_analytics(db: Session) -> list[dict]:
    """
    Calculate Today's and Monthly attendance analytics for each employee dynamically.
    """
    from app.services.time_calculator import (
        get_attendance_status, 
        calculate_late_minutes, 
        calculate_early_exit_minutes
    )
    from app.models.employee import Employee
    from app.models.user import User, Role
    from datetime import timedelta
    
    # Get all active workforce employees (both employee and hr roles)
    employees = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name).in_(["employee", "hr"]))
        .all()
    )
    
    today = datetime.now(APP_TIMEZONE).date()
    start_date = date(today.year, today.month, 1)
    
    # Build calendar list of days from start_date to today
    current_day = start_date
    calendar_days = []
    while current_day <= today:
        calendar_days.append(current_day)
        current_day += timedelta(days=1)
        
    analytics_data = []
    
    for emp in employees:
        # Fetch all attendance records for this employee in the current month
        records = (
            db.query(Attendance)
            .filter(Attendance.employee_id == emp.id, Attendance.date >= start_date, Attendance.date <= today)
            .all()
        )
        record_map = {r.date: r for r in records}
        
        # Today's status
        today_rec = record_map.get(today)
        if today_rec:
            calculate_attendance_metrics(today_rec)
            today_punch_in = today_rec.punch_in
            today_punch_out = today_rec.punch_out
            today_status = get_attendance_status(today_punch_in, today_punch_out, today)
            today_working_mins = today_rec.total_working_minutes or 0
            today_working_hours = f"{today_working_mins // 60}h {today_working_mins % 60}m"
        else:
            today_punch_in = None
            today_punch_out = None
            today_status = get_attendance_status(None, None, today)
            today_working_hours = "0h 0m"
            
        # Monthly aggregates
        present_days = 0
        absent_days = 0
        half_days = 0
        late_count = 0
        total_working_minutes = 0
        total_overtime_minutes = 0
        
        for d in calendar_days:
            rec = record_map.get(d)
            is_weekend = d.weekday() in (5, 6) # Sat, Sun
            
            if rec:
                calculate_attendance_metrics(rec)
                status = get_attendance_status(rec.punch_in, rec.punch_out, d)
                
                # Metrics
                if status == "Present":
                    present_days += 1
                elif status == "Half Day":
                    half_days += 1
                elif status == "Absent":
                    absent_days += 1
                elif status == "Working":
                    # Currently working today, let's treat it as present / working
                    pass
                
                # Late arrival
                late_mins = calculate_late_minutes(rec.punch_in)
                if late_mins > 0:
                    late_count += 1
                    
                total_working_minutes += (rec.total_working_minutes or 0)
                total_overtime_minutes += (rec.overtime_minutes or 0)
            else:
                # No record
                if is_weekend:
                    # Skip weekends if no punch
                    continue
                
                # Weekday with no punch
                status = get_attendance_status(None, None, d)
                if status == "Absent":
                    absent_days += 1
                    
        # Attendance % = (Present + 0.5 * Half Day) / (Present + Half Day + Absent) * 100
        total_work_days = present_days + half_days + absent_days
        attendance_percentage = 100.0
        if total_work_days > 0:
            attendance_percentage = round(((present_days + 0.5 * half_days) / total_work_days) * 100, 2)
            
        total_working_hours_str = f"{total_working_minutes // 60}h {total_working_minutes % 60}m"
        total_overtime_str = f"{total_overtime_minutes // 60}h {total_overtime_minutes % 60}m"
        
        analytics_data.append({
            "employeeId": emp.id,
            "employeeName": f"{emp.first_name} {emp.last_name}".strip(),
            "employeeCode": normalize_employee_code(emp.employee_code) if emp.employee_code else f"EMP-{emp.id:04d}",
            "department": emp.department or "Unassigned",
            "today": {
                "punchIn": today_punch_in.strftime("%H:%M") if today_punch_in else None,
                "punchOut": today_punch_out.strftime("%H:%M") if today_punch_out else None,
                "status": today_status,
                "workingHours": today_working_hours
            },
            "monthly": {
                "presentDays": present_days,
                "absentDays": absent_days,
                "halfDays": half_days,
                "lateCount": late_count,
                "totalWorkingHours": total_working_hours_str,
                "totalOvertime": total_overtime_str,
                "attendancePercentage": attendance_percentage
            }
        })
        
    return analytics_data

