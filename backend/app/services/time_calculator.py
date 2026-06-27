from datetime import time, datetime, date, timedelta
from zoneinfo import ZoneInfo
from app.models.attendance import Attendance

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

OFFICE_START_TIME = time(9, 0)
OFFICE_END_TIME = time(18, 0)
LUNCH_START_TIME = time(13, 0)
LUNCH_END_TIME = time(14, 0)
GRACE_PERIOD_MINUTES = 15
REQUIRED_WORKING_MINUTES = 480 # 8 hours
HALF_DAY_MINUTES = 120 # 2 hours

def _time_to_minutes(t: time) -> int:
    if not t:
        return 0
    return t.hour * 60 + t.minute

def calculate_overlap_minutes(punch_in: time, punch_out: time, window_start: time, window_end: time) -> int:
    """Calculate overlap duration in minutes between a punch span and a reference window."""
    if not punch_in or not punch_out:
        return 0
    in_mins = _time_to_minutes(punch_in)
    out_mins = _time_to_minutes(punch_out)
    win_start_mins = _time_to_minutes(window_start)
    win_end_mins = _time_to_minutes(window_end)
    
    if out_mins <= in_mins:
        return 0
        
    overlap_start = max(in_mins, win_start_mins)
    overlap_end = min(out_mins, win_end_mins)
    
    return max(0, overlap_end - overlap_start)

def calculate_late_minutes(punch_in: time) -> int:
    """Calculate late minutes based on 9:00 AM start and 15 minute grace period."""
    if not punch_in:
        return 0
    in_mins = _time_to_minutes(punch_in)
    start_mins = _time_to_minutes(OFFICE_START_TIME)
    
    # Grace period up to 09:15 AM
    if in_mins <= start_mins + GRACE_PERIOD_MINUTES:
        return 0
    return in_mins - start_mins

def calculate_early_exit_minutes(punch_out: time) -> int:
    """Calculate early exit minutes based on 18:00 PM shift end."""
    if not punch_out:
        return 0
    out_mins = _time_to_minutes(punch_out)
    end_mins = _time_to_minutes(OFFICE_END_TIME)
    
    if out_mins >= end_mins:
        return 0
    return end_mins - out_mins

def _get_approved_timeoff_hours(attendance_record: Attendance) -> float:
    from sqlalchemy.orm import object_session
    from app.models.timeoff import TimeOffRequest
    from sqlalchemy import func
    
    db = object_session(attendance_record)
    if db is not None:
        total = (
            db.query(func.coalesce(func.sum(TimeOffRequest.duration_hours), 0.0))
            .filter(
                TimeOffRequest.employee_id == attendance_record.employee_id,
                TimeOffRequest.date == attendance_record.date,
                TimeOffRequest.status.in_(["Approved", "Active", "Completed"]),
            )
            .scalar()
        )
        return float(total or 0.0)
    return 0.0

def get_attendance_status(
    punch_in: time | None,
    punch_out: time | None,
    record_date,
    current_dt: datetime | None = None,
    timeoff_duration_hours: float = 0.0
) -> str:
    """
    Centralized dynamic attendance status logic.
    Priority order:
    1. LEAVE (If full day of approved time off, status is LEAVE)
    2. WORKING (Punched In + No Punch Out)
    3. PRESENT / HALF_DAY / ABSENT (Based on Net Working Hours + Time-off Duration)
    4. NOT_MARKED (No Punch In and today, before cutoff 2:30 PM)
    5. ABSENT (No Punch In and past day OR today after cutoff 2:30 PM)
    """
    # If full day of time off (duration >= 8 hours)
    if timeoff_duration_hours >= 8.0:
        return "LEAVE"

    if punch_in is not None and punch_out is None:
        return "WORKING"
        
    if punch_in is not None and punch_out is not None:
        # Calculate net working minutes
        in_mins = _time_to_minutes(punch_in)
        out_mins = _time_to_minutes(punch_out)
        
        gross_minutes = max(0, out_mins - in_mins)
        lunch_overlap = calculate_overlap_minutes(punch_in, punch_out, LUNCH_START_TIME, LUNCH_END_TIME)
        net_minutes = max(0, gross_minutes - lunch_overlap)
        
        # Credit the time-off minutes
        timeoff_minutes = int(timeoff_duration_hours * 60)
        credited_minutes = net_minutes + timeoff_minutes
        
        # Late arrival within grace period tolerance
        required_mins = REQUIRED_WORKING_MINUTES
        if calculate_late_minutes(punch_in) == 0:
            late_deviation = max(0, in_mins - _time_to_minutes(OFFICE_START_TIME))
            required_mins -= late_deviation
            
        if credited_minutes >= required_mins:
            return "PRESENT"
        elif credited_minutes >= HALF_DAY_MINUTES:
            return "HALF_DAY"
        else:
            return "ABSENT"
            
    # Since punch_in is None, it's either LEAVE, HALF_DAY (if partial leave), NOT_MARKED or ABSENT
    timeoff_minutes = int(timeoff_duration_hours * 60)
    if timeoff_minutes >= REQUIRED_WORKING_MINUTES:
        return "LEAVE"
    elif timeoff_minutes >= HALF_DAY_MINUTES:
        return "HALF_DAY"

    if current_dt is None:
        current_dt = datetime.now(APP_TIMEZONE)
        
    today = current_dt.date()
    if record_date < today:
        # Past day and no punch in => ABSENT
        return "ABSENT"
        
    # It is today
    limit_time = time(14, 30) # 2:30 PM
    if current_dt.time() > limit_time:
        return "ABSENT"
        
    return "NOT_MARKED"

def determine_status(punch_in: time, punch_out: time, timeoff_duration_hours: float = 0.0) -> str:
    """Determine the status of attendance."""
    from datetime import date
    return get_attendance_status(punch_in, punch_out, date.today(), timeoff_duration_hours=timeoff_duration_hours)

def calculate_attendance_flags(attendance_record: Attendance) -> list[str]:
    flags = []
    if attendance_record.punch_in:
        late_mins = calculate_late_minutes(attendance_record.punch_in)
        if late_mins > 0:
            flags.append("LATE_ARRIVAL")
            
    if attendance_record.punch_out:
        early_mins = calculate_early_exit_minutes(attendance_record.punch_out)
        if early_mins > 0:
            flags.append("EARLY_EXIT")
            
        if attendance_record.overtime_minutes > 0:
            flags.append("OVERTIME")
            
    # Preserve existing AUTO_CHECKOUT, MISSED_PUNCH, REGULARIZED flags if set
    for f in ["AUTO_CHECKOUT", "MISSED_PUNCH", "REGULARIZED"]:
        if f in attendance_record.flags:
            flags.append(f)
            
    return list(set(flags))

def calculate_times(attendance_record: Attendance, timeoff_duration_hours: float = 0.0):
    """Calculates working hours, overtime, break, and updates the attendance record status."""
    # Resolve approved timeoff duration from session if not passed explicitly
    if timeoff_duration_hours == 0.0:
        timeoff_duration_hours = _get_approved_timeoff_hours(attendance_record)

    if not attendance_record.punch_in:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.break_minutes = int(timeoff_duration_hours * 60)
        attendance_record.status = get_attendance_status(None, None, attendance_record.date, timeoff_duration_hours=timeoff_duration_hours)
        attendance_record.flags = []
        return

    if not attendance_record.punch_out:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.break_minutes = int(timeoff_duration_hours * 60)
        attendance_record.status = "WORKING"
        # Overtime flags if they clicked continue working
        flags = []
        if attendance_record.overtime_approved:
            flags.append("OVERTIME")
        # Keep other flags
        for f in ["AUTO_CHECKOUT", "MISSED_PUNCH", "REGULARIZED"]:
            if f in attendance_record.flags:
                flags.append(f)
        attendance_record.flags = flags
        return

    in_minutes = _time_to_minutes(attendance_record.punch_in)
    out_minutes = _time_to_minutes(attendance_record.punch_out)
    
    if out_minutes <= in_minutes:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.status = "ABSENT"
        attendance_record.flags = []
        return
        
    gross_minutes = out_minutes - in_minutes
    lunch_minutes = calculate_overlap_minutes(attendance_record.punch_in, attendance_record.punch_out, LUNCH_START_TIME, LUNCH_END_TIME)
    
    # Calculate time-off overlap with punch interval
    timeoff_overlap_minutes = 0
    from sqlalchemy.orm import object_session
    db = object_session(attendance_record)
    if db is not None:
        from app.models.timeoff import TimeOffRequest
        timeoff_reqs = (
            db.query(TimeOffRequest)
            .filter(
                TimeOffRequest.employee_id == attendance_record.employee_id,
                TimeOffRequest.date == attendance_record.date,
                TimeOffRequest.status.in_(["Approved", "Active", "Completed"]),
            )
            .all()
        )
        for r in timeoff_reqs:
            st = r.start_time or OFFICE_START_TIME
            et = r.end_time or OFFICE_END_TIME
            overlap = calculate_overlap_minutes(
                attendance_record.punch_in,
                attendance_record.punch_out,
                st,
                et
            )
            timeoff_overlap_minutes += overlap
    else:
        # Fallback to subtracting the whole duration if no db session (e.g. standard tests)
        timeoff_overlap_minutes = min(gross_minutes, int(timeoff_duration_hours * 60))

    net_working_minutes = max(0, gross_minutes - lunch_minutes - timeoff_overlap_minutes)
    
    overtime_minutes = 0
    if attendance_record.overtime_approved and net_working_minutes > REQUIRED_WORKING_MINUTES:
        overtime_minutes = min(120, net_working_minutes - REQUIRED_WORKING_MINUTES)
    
    attendance_record.total_working_minutes = net_working_minutes
    attendance_record.overtime_minutes = overtime_minutes
    attendance_record.grand_total_minutes = net_working_minutes + overtime_minutes
    
    timeoff_minutes = int(timeoff_duration_hours * 60)
    attendance_record.break_minutes = lunch_minutes + timeoff_minutes
    
    attendance_record.status = get_attendance_status(
        attendance_record.punch_in,
        attendance_record.punch_out,
        attendance_record.date,
        timeoff_duration_hours=timeoff_duration_hours
    )
    attendance_record.flags = calculate_attendance_flags(attendance_record)
