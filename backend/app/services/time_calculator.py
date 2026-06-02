from datetime import time, datetime, timedelta
from app.models.attendance import Attendance

OFFICE_START_TIME = time(9, 0)
OFFICE_END_TIME = time(18, 0)
FIXED_BREAK_MINUTES = 55

def _time_to_minutes(t: time) -> int:
    if not t:
        return 0
    return t.hour * 60 + t.minute

def normalize_punch_in(punch_in_time: time) -> time:
    """Normalizes punch in time. Before 09:00 AM becomes 09:00 AM."""
    if _time_to_minutes(punch_in_time) < _time_to_minutes(OFFICE_START_TIME):
        return OFFICE_START_TIME
    return punch_in_time

from zoneinfo import ZoneInfo
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

def get_attendance_status(punch_in: time | None, punch_out: time | None, record_date, current_dt: datetime | None = None) -> str:
    """
    Centralized dynamic attendance status logic.
    Priority order:
    1. Present (Punch Out completed)
    2. Working (Logged In + Punch In + No Punch Out)
    3. Not Marked (Logged In + No Punch In and time <= 2:30 PM)
    4. Absent (Not Logged In OR No Punch In after 2:30 PM)
    """
    if punch_in is not None and punch_out is not None:
        return "Present"
        
    if punch_in is not None and punch_out is None:
        return "Working"
        
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
    """Calculates working hours, overtime, and updates the attendance record."""
    if not attendance_record.punch_in or not attendance_record.punch_out:
        # Incomplete punches
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.break_minutes = int(timeoff_duration_hours * 60)
        return

    in_minutes = _time_to_minutes(attendance_record.punch_in)
    out_minutes = _time_to_minutes(attendance_record.punch_out)
    
    if out_minutes <= in_minutes:
        # Invalid entry or same time punch out
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        return
        
    # Gross minutes
    gross_minutes = out_minutes - in_minutes
    
    # Deduct fixed lunch if the period spans lunch time (13:00 - 14:00).
    lunch_minutes = FIXED_BREAK_MINUTES if attendance_record.punch_in < time(13, 0) and attendance_record.punch_out > time(14, 0) else 0
    
    timeoff_minutes = int(timeoff_duration_hours * 60)
    
    # Total Working Hours = (PunchOut - PunchIn) - Lunch Break - TimeOff
    total_working_minutes = gross_minutes - lunch_minutes - timeoff_minutes
    if total_working_minutes < 0:
        total_working_minutes = 0
        
    # Overtime Calculation
    # If PunchOut > 18:00
    office_end_minutes = _time_to_minutes(OFFICE_END_TIME)
    if out_minutes > office_end_minutes:
        overtime_minutes = out_minutes - office_end_minutes
    else:
        overtime_minutes = 0
        
    attendance_record.total_working_minutes = total_working_minutes
    attendance_record.overtime_minutes = overtime_minutes
    attendance_record.grand_total_minutes = total_working_minutes + overtime_minutes
    attendance_record.break_minutes = lunch_minutes + timeoff_minutes
    
    # Update Status
    attendance_record.status = determine_status(attendance_record.punch_in, attendance_record.punch_out, timeoff_duration_hours)
