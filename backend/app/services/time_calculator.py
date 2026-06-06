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
HALF_DAY_MINUTES = 240 # 4 hours

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

def get_attendance_status(punch_in: time | None, punch_out: time | None, record_date, current_dt: datetime | None = None) -> str:
    """
    Centralized dynamic attendance status logic.
    Priority order:
    1. Working (Punched In + No Punch Out)
    2. Present / Half Day / Absent (If Punch In & Punch Out completed, based on Net Working Hours)
    3. Not Marked (No Punch In and today, before cutoff 2:30 PM)
    4. Absent (No Punch In and past day OR today after cutoff 2:30 PM)
    """
    if punch_in is not None and punch_out is None:
        return "Working"
        
    if punch_in is not None and punch_out is not None:
        # Calculate net working minutes
        in_mins = _time_to_minutes(punch_in)
        out_mins = _time_to_minutes(punch_out)
        
        gross_minutes = max(0, out_mins - in_mins)
        lunch_overlap = calculate_overlap_minutes(punch_in, punch_out, LUNCH_START_TIME, LUNCH_END_TIME)
        net_minutes = max(0, gross_minutes - lunch_overlap)
        
        if net_minutes >= REQUIRED_WORKING_MINUTES:
            return "Present"
        elif net_minutes >= HALF_DAY_MINUTES:
            return "Half Day"
        else:
            return "Absent"
            
    # Since punch_in is None, it's either Not Marked or Absent
    if current_dt is None:
        current_dt = datetime.now(APP_TIMEZONE)
        
    today = current_dt.date()
    if record_date < today:
        # Past day and no punch in => Absent
        return "Absent"
        
    # It is today
    limit_time = time(14, 30) # 2:30 PM
    if current_dt.time() > limit_time:
        return "Absent"
        
    return "Not Marked"

def determine_status(punch_in: time, punch_out: time, timeoff_duration_hours: float = 0.0) -> str:
    """Determine the status of attendance."""
    from datetime import date
    return get_attendance_status(punch_in, punch_out, date.today())

def calculate_times(attendance_record: Attendance, timeoff_duration_hours: float = 0.0):
    """Calculates working hours, overtime, break, and updates the attendance record status."""
    if not attendance_record.punch_in:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.break_minutes = int(timeoff_duration_hours * 60)
        attendance_record.status = get_attendance_status(None, None, attendance_record.date)
        return

    if not attendance_record.punch_out:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.break_minutes = int(timeoff_duration_hours * 60)
        attendance_record.status = "Working"
        return

    in_minutes = _time_to_minutes(attendance_record.punch_in)
    out_minutes = _time_to_minutes(attendance_record.punch_out)
    
    if out_minutes <= in_minutes:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.status = "Absent"
        return
        
    gross_minutes = out_minutes - in_minutes
    lunch_minutes = calculate_overlap_minutes(attendance_record.punch_in, attendance_record.punch_out, LUNCH_START_TIME, LUNCH_END_TIME)
    timeoff_minutes = int(timeoff_duration_hours * 60)
    
    net_working_minutes = max(0, gross_minutes - lunch_minutes - timeoff_minutes)
    overtime_minutes = max(0, net_working_minutes - REQUIRED_WORKING_MINUTES)
    
    attendance_record.total_working_minutes = net_working_minutes
    attendance_record.overtime_minutes = overtime_minutes
    attendance_record.grand_total_minutes = net_working_minutes + overtime_minutes
    attendance_record.break_minutes = lunch_minutes + timeoff_minutes
    
    attendance_record.status = get_attendance_status(attendance_record.punch_in, attendance_record.punch_out, attendance_record.date)
