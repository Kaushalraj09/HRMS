from datetime import time, date, datetime
from zoneinfo import ZoneInfo
from app.services.time_calculator import get_attendance_status

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

def test_status_present():
    # Punch In = Yes, Punch Out = Yes
    assert get_attendance_status(time(9, 0), time(18, 0), date(2026, 6, 2)) == "Present"

def test_status_working():
    # Punch In = Yes, Punch Out = No
    assert get_attendance_status(time(9, 0), None, date(2026, 6, 2)) == "Working"

def test_status_not_marked_before_cutoff():
    # Logged In = Yes, Punch In = No, Current Time = 11:00 AM (<= 2:30 PM)
    record_date = date(2026, 6, 2)
    current_dt = datetime(2026, 6, 2, 11, 0, tzinfo=APP_TIMEZONE)
    assert get_attendance_status(None, None, record_date, current_dt) == "Not Marked"

def test_status_absent_after_cutoff():
    # Logged In = Yes, Punch In = No, Current Time = 3:00 PM (> 2:30 PM)
    record_date = date(2026, 6, 2)
    current_dt = datetime(2026, 6, 2, 15, 0, tzinfo=APP_TIMEZONE)
    assert get_attendance_status(None, None, record_date, current_dt) == "Absent"

def test_status_absent_past_day():
    # Past day, no punch in
    record_date = date(2026, 6, 1)
    current_dt = datetime(2026, 6, 2, 10, 0, tzinfo=APP_TIMEZONE)
    assert get_attendance_status(None, None, record_date, current_dt) == "Absent"
