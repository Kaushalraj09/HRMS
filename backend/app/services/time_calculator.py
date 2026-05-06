from datetime import time, datetime, timedelta
from app.models.attendance import Attendance

OFFICE_START_TIME = time(9, 0)
OFFICE_END_TIME = time(18, 0)
LUNCH_BREAK_HOURS = 1.0

def _time_to_minutes(t: time) -> int:
    if not t:
        return 0
    return t.hour * 60 + t.minute

def normalize_punch_in(punch_in_time: time) -> time:
    """Normalizes punch in time. Before 09:00 AM becomes 09:00 AM."""
    if _time_to_minutes(punch_in_time) < _time_to_minutes(OFFICE_START_TIME):
        return OFFICE_START_TIME
    return punch_in_time

def determine_status(punch_in: time, punch_out: time, timeoff_duration_hours: float) -> str:
    """Determine the status of attendance."""
    if not punch_in:
        return "Not Marked"
    
    # If they took an 8-hour leave, it's a full day leave
    if timeoff_duration_hours >= 8.0:
        return "Leave"
        
    # If partial leave is taken, we might mark as Half-Day or Present depending on rules
    if timeoff_duration_hours > 0 and timeoff_duration_hours < 8.0:
        return "Half-Day"

    # Late if punched in after 09:00 AM
    if _time_to_minutes(punch_in) > _time_to_minutes(OFFICE_START_TIME):
        return "Late"
        
    if punch_in and not punch_out:
        return "Checked In"

    return "Present"

def calculate_times(attendance_record: Attendance, timeoff_duration_hours: float = 0.0):
    """Calculates working hours, overtime, and updates the attendance record."""
    if not attendance_record.check_in or not attendance_record.check_out:
        # Incomplete punches
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.break_minutes = int(timeoff_duration_hours * 60)
        return

    in_minutes = _time_to_minutes(attendance_record.check_in)
    out_minutes = _time_to_minutes(attendance_record.check_out)
    
    if out_minutes <= in_minutes:
        # Invalid entry or same time punch out
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        return
        
    # Gross minutes
    gross_minutes = out_minutes - in_minutes
    
    # Deduct Lunch if the period spans lunch time (13:00 - 14:00)
    # Simple rule: if total time > 4 hours, deduct 1 hour lunch
    lunch_minutes = int(LUNCH_BREAK_HOURS * 60) if gross_minutes > (4 * 60) else 0
    
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
    attendance_record.status = determine_status(attendance_record.check_in, attendance_record.check_out, timeoff_duration_hours)
