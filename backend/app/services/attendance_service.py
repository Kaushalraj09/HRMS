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
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def calculate_attendance_metrics(attendance: Attendance) -> None:
    """
    Calculate working minutes, break, overtime, and grand total based on check_in and check_out times.
    Uses the new enterprise rules from time_calculator.
    """
    from app.services.time_calculator import calculate_times
    calculate_times(attendance)




def _shift_elapsed_seconds(now: datetime | None, start_t: time, end_t: time) -> int:
    """
    Calculate elapsed seconds in shift from start to current time.
    """
    current = now or datetime.now(APP_TIMEZONE)
    current_seconds = current.hour * 3600 + current.minute * 60 + current.second
    shift_start_seconds = start_t.hour * 3600 + start_t.minute * 60
    shift_end_seconds = end_t.hour * 3600 + end_t.minute * 60

    if shift_end_seconds < shift_start_seconds:
        # Crosses midnight
        total_sec = (86400 - shift_start_seconds) + shift_end_seconds
        if current_seconds >= shift_start_seconds:
            return min(total_sec, current_seconds - shift_start_seconds)
        elif current_seconds <= shift_end_seconds:
            return min(total_sec, (86400 - shift_start_seconds) + current_seconds)
        return 0
    else:
        total_sec = shift_end_seconds - shift_start_seconds
        if current_seconds <= shift_start_seconds:
            return 0
        if current_seconds >= shift_end_seconds:
            return total_sec
        return current_seconds - shift_start_seconds


def get_attendance_status_with_timeoff(db: Session | None, employee_id: int, punch_in_time, punch_out_time, record_date: date, current_dt=None) -> str:
    from app.services.time_calculator import get_attendance_status
    
    status_map = {
        "WORKING": "Working",
        "PRESENT": "Present",
        "HALF_DAY": "Half Day",
        "ABSENT": "Absent",
        "NOT_MARKED": "Not Marked",
        "LEAVE": "Time Off",
        "PRESENT_TODAY": "Present",
        "AUTO_CHECKOUT": "Present",
        "AUTO CHECKED-OUT": "Present",
    }
    
    if not db:
        status_val = get_attendance_status(punch_in_time, punch_out_time, record_date, current_dt)
        return status_map.get(status_val, status_val)
        
    # Check if there is an existing record
    existing_record = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == record_date
    ).first()
    if existing_record and existing_record.status in ("PRESENT", "Present") and existing_record.requires_regularization and "AUTO_CHECKOUT" in existing_record.flags:
        return "Present"
    if existing_record and existing_record.status == "Auto Checked-out":
        return "Present"
        
    status_val = get_attendance_status(punch_in_time, punch_out_time, record_date, current_dt)
    
    from app.models.timeoff import TimeOffRequest
    timeoff = db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id,
        TimeOffRequest.date == record_date,
        TimeOffRequest.status.in_(["Approved", "Active", "Completed"])
    ).first()
    
    if timeoff:
        if timeoff.leave_type in ("Full-Day", "Full Day"):
            return "Time Off"
        elif timeoff.leave_type in ("Half-Day", "Half Day"):
            if punch_in_time is not None and punch_out_time is None:
                return "Working"
            return "Half Day"
            
    return status_map.get(status_val, status_val)


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
    from app.models.timeoff import TimeOffRequest
    from sqlalchemy import func
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





def log_audit_trail_sync(db: Session, event: str, employee_id: int, details: str = None) -> None:
    from app.models.attendance import AttendanceAuditTrail
    audit = AttendanceAuditTrail(
        event=event,
        employee_id=employee_id,
        details=details
    )
    db.add(audit)
    db.commit()

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
        emp_code = employee.employee_code if employee else f"{employee_id:04d}"
        
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
            status="WORKING",
        )
        db.add(attendance)
        db.flush()
    else:
        # Update existing attendance record
        attendance.is_working = 1
        attendance.work_mode = work_mode
        attendance.status = "WORKING"
    
    # Set punch-in with location and image (first check-in of the day)
    attendance.punch_in = current.time()
    attendance.punch_in_latitude = latitude
    attendance.punch_in_longitude = longitude
    attendance.punch_in_address = address
    attendance.punch_in_image = image
    
    db.commit()
    db.refresh(attendance)
    try:
        from app.services.dashboard_service import invalidate_dashboard_cache
        invalidate_dashboard_cache(db, keys=["dashboard:admin", "dashboard:hr"])
    except Exception:
        pass
    
    log_audit_trail_sync(db, "PUNCH_IN", employee_id, f"Punched in via {work_mode} at {current.time()}")
    
    return to_attendance_response(attendance, db)

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
    attendance.status = "PRESENT"
    
    # Calculate metrics
    calculate_attendance_metrics(attendance)
    
    db.commit()
    db.refresh(attendance)
    try:
        from app.services.dashboard_service import invalidate_dashboard_cache
        invalidate_dashboard_cache(db, keys=["dashboard:admin", "dashboard:hr"])
    except Exception:
        pass
    
    log_audit_trail_sync(db, "PUNCH_OUT", employee_id, f"Punched out via {work_mode} at {current.time()}")
    
    return to_attendance_response(attendance, db)

def get_today_state(db: Session, employee_id: int) -> dict:
    """
    Get current attendance state for today using assigned Shift Master data.
    """
    from app.domain.attendance.repositories.shift_repository import ShiftRepository
    current = datetime.now(APP_TIMEZONE)
    today = current.date()
    
    shift = ShiftRepository.get_assigned_shift(db, employee_id, today)
    
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == today)
        .first()
    )
    
    if not attendance:
        # Automatically register pre-punch record
        attendance = Attendance(
            employee_id=employee_id,
            shift_id=shift.id,
            date=today,
            is_working=0,
            work_mode="Office",
            status=get_attendance_status(None, None, today, current, shift=shift),
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
    elif not attendance.shift_id:
        attendance.shift_id = shift.id
        db.commit()
        
    # Calculate total worked seconds
    worked_seconds = 0
    if attendance and attendance.punch_in and attendance.punch_out:
        check_in_dt = datetime.combine(today, attendance.punch_in, tzinfo=APP_TIMEZONE)
        check_out_dt = datetime.combine(today, attendance.punch_out, tzinfo=APP_TIMEZONE)
        worked_seconds = int((check_out_dt - check_in_dt).total_seconds())
    elif attendance and attendance.punch_in and attendance.is_working:
        check_in_dt = datetime.combine(today, attendance.punch_in, tzinfo=APP_TIMEZONE)
        worked_seconds = int((current - check_in_dt).total_seconds())
    
    approved_hours = get_timeoff_duration_today(db, employee_id)
    approved_seconds = int(round(approved_hours * 3600))
    
    shift_total_seconds = (shift.required_work_minutes or 480) * 60
    remaining_seconds = max(0, shift_total_seconds - worked_seconds - approved_seconds)
    
    # Strict reliance on assigned shift timings
    shift_start_time = shift.start_time
    shift_end_time = shift.end_time
    if not shift_start_time or not shift_end_time:
        # Fallback only for data integrity issues, but logic demands shift times
        shift_start_time = shift_start_time or time(9, 0)
        shift_end_time = shift_end_time or time(18, 0)
        
    shift_elapsed_seconds = _shift_elapsed_seconds(current, shift_start_time, shift_end_time)
    
    # Check if yesterday was auto checked out and has not yet been regularized
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    yesterday_rec = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == yesterday)
        .first()
    )
    yesterday_auto_checked_out = False
    if yesterday_rec and yesterday_rec.requires_regularization and "AUTO_CHECKOUT" in yesterday_rec.flags:
        yesterday_auto_checked_out = True
        from app.models.attendance import AttendanceRegularizationRequest
        pending_request = (
            db.query(AttendanceRegularizationRequest)
            .filter(
                AttendanceRegularizationRequest.employee_id == employee_id,
                AttendanceRegularizationRequest.attendance_date == yesterday,
                AttendanceRegularizationRequest.status == "pending"
            )
            .first()
        )
        if pending_request:
            yesterday_auto_checked_out = False
    
    # Calculate lunch timings
    from app.domain.attendance.services.shift_calculation_service import ShiftCalculationService
    lunch_start, lunch_end = ShiftCalculationService.calculate_lunch_window(shift)

    return {
        "employeeId": employee_id,
        "isWorking": bool(attendance and attendance.is_working),
        "status": get_attendance_status_with_timeoff(db, employee_id, attendance.punch_in, attendance.punch_out, attendance.date, current),
        "totalWorkedSeconds": worked_seconds,
        "approvedSeconds": approved_seconds,
        "remainingSeconds": remaining_seconds,
        "shiftTotalSeconds": shift_total_seconds,
        "shiftElapsedSeconds": shift_elapsed_seconds,
        "shiftStart": shift_start_time.strftime("%I:%M %p"),
        "shiftEnd": shift_end_time.strftime("%I:%M %p"),
        "shiftName": shift.name,
        "shiftCode": shift.code,
        "lunchStart": lunch_start.strftime("%I:%M %p"),
        "lunchEnd": lunch_end.strftime("%I:%M %p"),
        "graceMinutes": shift.grace_minutes or 30,
        "lunchDurationMinutes": shift.lunch_duration_minutes or 40,
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
        "yesterdayAutoCheckedOut": yesterday_auto_checked_out,
        "flags": attendance.flags if attendance else [],
        "requiresRegularization": attendance.requires_regularization if attendance else False,
        "overtimeApproved": attendance.overtime_approved if attendance else False,
        "overtimeExtended": attendance.overtime_extended if attendance else False,
        "maxOvertimeMinutes": shift.max_overtime_minutes or 120,
        "overtimeAllowed": shift.overtime_allowed if shift.overtime_allowed is not None else True,
        "overtimeStartTime": (shift.overtime_start_time or shift_end_time).strftime("%I:%M %p"),
    }

def _normalize_attendance_status(status: str) -> str:
    if not status:
        return ""
    val = status.strip().lower().replace("_", " ").replace("-", " ")
    mapping = {
        "present": "present",
        "working": "working",
        "absent": "absent",
        "not marked": "not marked",
        "notmarked": "not marked",
        "half day": "half day",
        "half-day": "half day",
        "leave": "time off",
        "time off": "time off",
        "holiday": "holiday",
        "week off": "week off",
    }
    return mapping.get(val, val)


def _matches_computed_status(db: Session, record: Attendance, status_filter: str) -> bool:
    if not status_filter:
        return True
    requested = _normalize_attendance_status(status_filter)
    actual_raw = get_attendance_status_with_timeoff(db, record.employee_id, record.punch_in, record.punch_out, record.date)
    actual = _normalize_attendance_status(actual_raw)
    return requested == actual or requested in actual


def _attendance_metrics(db: Session, records: list[Attendance]) -> dict:
    metrics = {
        "present": 0,
        "working": 0,
        "absent": 0,
        "notMarked": 0,
    }
    for record in records:
        status_value = get_attendance_status_with_timeoff(db, record.employee_id, record.punch_in, record.punch_out, record.date)
        status_upper = status_value.upper()
        if status_upper in ("PRESENT", "AUTO_CHECKOUT", "AUTO CHECKED-OUT"):
            metrics["present"] += 1
        elif status_upper == "WORKING":
            metrics["working"] += 1
        elif status_upper == "ABSENT":
            metrics["absent"] += 1
        elif status_upper in ("NOT_MARKED", "NOT MARKED"):
            metrics["notMarked"] += 1
        elif status_upper in ("HALF_DAY", "HALF DAY", "LEAVE", "TIME OFF"):
            metrics["present"] += 1
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
    return [record for record in records if _matches_computed_status(db, record, status_filter)]


def to_attendance_response(record: Attendance, db: Session = None) -> AttendanceResponse:
    """
    Convert attendance record to response schema with dynamic shift information.
    """
    calculate_attendance_metrics(record)
    
    from app.domain.attendance.repositories.shift_repository import ShiftRepository
    from app.services.time_calculator import calculate_late_minutes, calculate_early_exit_minutes

    shift_obj = record.shift
    if not shift_obj and db:
        shift_obj = ShiftRepository.get_assigned_shift(db, record.employee_id, record.date)

    late_minutes = calculate_late_minutes(record.punch_in, shift_obj)
    early_exit_minutes = calculate_early_exit_minutes(record.punch_out, shift_obj)
    status_val = get_attendance_status_with_timeoff(db, record.employee_id, record.punch_in, record.punch_out, record.date)
    
    emp_name = None
    if record.employee:
        emp_name = f"{record.employee.first_name} {record.employee.last_name}".strip()
    elif db:
        emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
        if emp:
            emp_name = f"{emp.first_name} {emp.last_name}".strip()

    shift_dict = None
    if shift_obj:
        shift_dict = {
            "id": shift_obj.id,
            "name": shift_obj.name,
            "code": shift_obj.code,
            "start_time": shift_obj.start_time.strftime("%H:%M") if shift_obj.start_time else "09:00",
            "end_time": shift_obj.end_time.strftime("%H:%M") if shift_obj.end_time else "18:00",
            "working_hours": float(shift_obj.working_hours or 8.0),
            "grace_minutes": shift_obj.grace_minutes or 30,
            "lunch_duration": shift_obj.lunch_duration_minutes or 40,
            "half_day_hours": float(shift_obj.half_day_hours or 4.0),
            "present_hours": float(shift_obj.present_hours or 8.0),
            "is_night_shift": bool(shift_obj.is_night_shift),
        }

    return AttendanceResponse(
        id=record.id,
        employee_id=record.employee_id,
        shift_id=shift_obj.id if shift_obj else None,
        employee=emp_name or f"Employee #{record.employee_id}",
        shift=shift_dict,
        date=record.date,
        scheduled_start=record.scheduled_start,
        scheduled_end=record.scheduled_end,
        task_description=record.task_description,
        punch_in=record.punch_in,
        punch_out=record.punch_out,
        status=status_val,
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
        flags=record.flags,
        checkout_source=record.checkout_source,
        requires_regularization=record.requires_regularization,
        overtime_approved=record.overtime_approved,
        overtime_start=record.overtime_start,
        overtime_end=record.overtime_end,
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
    
    return to_attendance_response(record, db)

def get_computed_status_expression(db: Session, current_dt=None):
    from sqlalchemy import case, and_, or_, cast, Integer, Date, String
    from app.models.timeoff import TimeOffRequest

    if current_dt is None:
        current_dt = datetime.now(APP_TIMEZONE)
    today = current_dt.date()
    current_time = current_dt.time()

    # Subquery for approved timeoff hours for this record
    timeoff_hours_expr = (
        db.query(func.coalesce(func.sum(TimeOffRequest.duration_hours), 0.0))
        .filter(
            TimeOffRequest.employee_id == Attendance.employee_id,
            TimeOffRequest.date == Attendance.date,
            TimeOffRequest.status.in_(["Approved", "Active", "Completed"])
        )
        .correlate(Attendance)
        .scalar_subquery()
    )

    # Case 1: Time Off (full day leave)
    cond_timeoff_full = timeoff_hours_expr >= 8.0

    # Case 2: Explicitly Marked status / Auto Checked-out
    cond_auto_checkout_flag = and_(
        Attendance.status.in_(["PRESENT", "Present"]),
        Attendance.requires_regularization == True,
        Attendance._flags.like("%AUTO_CHECKOUT%")
    )
    cond_present_status = or_(
        Attendance.status == "Auto Checked-out",
        cond_auto_checkout_flag
    )

    # Case 3: Working (punched in but not punched out)
    cond_working = and_(
        Attendance.punch_in.isnot(None),
        Attendance.punch_out.is_(None)
    )

    # Case 4: Punched in and out
    credited_mins = Attendance.total_working_minutes + func.cast(timeoff_hours_expr * 60, Integer)

    cond_present_work = and_(
        Attendance.punch_in.isnot(None),
        Attendance.punch_out.isnot(None),
        credited_mins >= 480
    )

    cond_half_day_work = and_(
        Attendance.punch_in.isnot(None),
        Attendance.punch_out.isnot(None),
        credited_mins >= 120,
        credited_mins < 480
    )

    # Case 5: No punch in
    cond_half_day_leave = and_(
        Attendance.punch_in.is_(None),
        timeoff_hours_expr >= 2.0,
        timeoff_hours_expr < 8.0
    )

    cond_leave_no_punch = and_(
        Attendance.punch_in.is_(None),
        timeoff_hours_expr >= 8.0
    )

    # Not Marked condition
    cond_not_marked = and_(
        Attendance.punch_in.is_(None),
        timeoff_hours_expr < 2.0,
        Attendance.date == today,
        literal(current_time) <= time(14, 30)
    )

    # Absent condition
    cond_absent_no_punch = and_(
        Attendance.punch_in.is_(None),
        timeoff_hours_expr < 2.0,
        or_(
            Attendance.date < today,
            and_(
                Attendance.date == today,
                literal(current_time) > time(14, 30)
            )
        )
    )

    cond_absent_work = and_(
        Attendance.punch_in.isnot(None),
        Attendance.punch_out.isnot(None),
        credited_mins < 120
    )

    status_expr = case(
        (cond_timeoff_full, "Time Off"),
        (cond_present_status, "Present"),
        (cond_working, "Working"),
        (cond_present_work, "Present"),
        (cond_half_day_work, "Half Day"),
        (cond_leave_no_punch, "Time Off"),
        (cond_half_day_leave, "Half Day"),
        (cond_not_marked, "Not Marked"),
        (cond_absent_no_punch, "Absent"),
        (cond_absent_work, "Absent"),
        else_="Absent"
    )
    return status_expr

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
    """
    from sqlalchemy import case, and_, or_
    from app.models.user import User, Role

    today = datetime.now(APP_TIMEZONE).date()
    query = (
        db.query(Attendance)
        .join(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name) != "admin")
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

    # Apply computed status filter at the database level if specified
    status_expr = get_computed_status_expression(db)
    if status_filter:
        normalized_requested = _normalize_attendance_status(status_filter).lower()
        if normalized_requested == "present":
            query = query.filter(status_expr == "Present")
        elif normalized_requested == "working":
            query = query.filter(status_expr == "Working")
        elif normalized_requested == "absent":
            query = query.filter(status_expr == "Absent")
        elif normalized_requested == "not marked":
            query = query.filter(status_expr == "Not Marked")
        elif normalized_requested == "half day":
            query = query.filter(status_expr == "Half Day")
        elif normalized_requested == "time off":
            query = query.filter(status_expr == "Time Off")

    # Now count total matching records
    total = query.count()

    # Re-apply the filters to calculate metrics for all matching records using a single aggregate query
    m_query = db.query(
        func.sum(case((status_expr == "Present", 1), else_=0)).label("present"),
        func.sum(case((status_expr == "Working", 1), else_=0)).label("working"),
        func.sum(case((status_expr == "Absent", 1), else_=0)).label("absent"),
        func.sum(case((status_expr == "Not Marked", 1), else_=0)).label("not_marked")
    ).select_from(Attendance).join(Employee).join(User, Employee.user_id == User.id).join(Role, User.role_id == Role.id).filter(func.lower(Role.name) != "admin").filter(Attendance.date <= today)

    if from_date:
        m_query = m_query.filter(Attendance.date >= from_date)
    if to_date:
        m_query = m_query.filter(Attendance.date <= to_date)
    if department:
        m_query = m_query.filter(Employee.department == department)
    if location:
        m_query = m_query.filter(Attendance.work_mode == location)
    if search_value:
        m_query = m_query.filter(
            or_(
                Employee.first_name.ilike(like_value),
                Employee.last_name.ilike(like_value),
                full_name.ilike(like_value),
                Employee.employee_code.ilike(like_value),
            )
        )
    if status_filter:
        if normalized_requested == "present":
            m_query = m_query.filter(status_expr == "Present")
        elif normalized_requested == "working":
            m_query = m_query.filter(status_expr == "Working")
        elif normalized_requested == "absent":
            m_query = m_query.filter(status_expr == "Absent")
        elif normalized_requested == "not marked":
            m_query = m_query.filter(status_expr == "Not Marked")
        elif normalized_requested == "half day":
            m_query = m_query.filter(status_expr == "Half Day")
        elif normalized_requested == "time off":
            m_query = m_query.filter(status_expr == "Time Off")

    metrics_row = m_query.first()
    metrics = {
        "present": int(metrics_row.present or 0),
        "working": int(metrics_row.working or 0),
        "absent": int(metrics_row.absent or 0),
        "notMarked": int(metrics_row.not_marked or 0),
    }

    # Now, paginate database-side
    paged_records = query.order_by(
        Attendance.date.desc(),
        Attendance.punch_in.desc().nulls_last(),
        Attendance.id.desc(),
    ).offset((page - 1) * limit).limit(limit).all()

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
            "status": get_attendance_status_with_timeoff(db, record.employee_id, record.punch_in, record.punch_out, record.date),
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
            "flags": record.flags,
            "checkoutSource": record.checkout_source,
            "requiresRegularization": record.requires_regularization,
            "overtimeApproved": record.overtime_approved,
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
            status=get_attendance_status_with_timeoff(db, employee_id, None, None, today, current),
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
        .filter(
            func.lower(Role.name).in_(["employee", "hr"]),
            Employee.status != "Deleted",
            User.status != "Deleted"
        )
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
            today_status = get_attendance_status_with_timeoff(db, emp.id, today_punch_in, today_punch_out, today)
            today_working_mins = today_rec.total_working_minutes or 0
            today_working_hours = f"{today_working_mins // 60}h {today_working_mins % 60}m"
        else:
            today_punch_in = None
            today_punch_out = None
            today_status = get_attendance_status_with_timeoff(db, emp.id, None, None, today)
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
                status = get_attendance_status_with_timeoff(db, emp.id, rec.punch_in, rec.punch_out, d)
                
                # Metrics
                if status in ("Present", "Time Off", "Auto Checked-out"):
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
                status = get_attendance_status_with_timeoff(db, emp.id, None, None, d)
                if status == "Absent":
                    absent_days += 1
                elif status in ("Present", "Time Off", "Auto Checked-out"):
                    present_days += 1
                elif status == "Half Day":
                    half_days += 1
                    
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
            "employeeCode": normalize_employee_code(emp.employee_code) if emp.employee_code else f"{emp.id:04d}",
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

