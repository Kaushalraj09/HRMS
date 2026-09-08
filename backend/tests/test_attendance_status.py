from datetime import time, date, datetime
from zoneinfo import ZoneInfo
from app.services.time_calculator import get_attendance_status

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

def test_status_present():
    # Punch In = Yes, Punch Out = Yes
    assert get_attendance_status(time(9, 0), time(18, 0), date(2026, 6, 2)) == "PRESENT"

def test_status_working():
    # Punch In = Yes, Punch Out = No
    assert get_attendance_status(time(9, 0), None, date(2026, 6, 2)) == "WORKING"

def test_status_not_marked_before_cutoff():
    # Logged In = Yes, Punch In = No, Current Time = 11:00 AM (<= 2:30 PM)
    record_date = date(2026, 6, 2)
    current_dt = datetime(2026, 6, 2, 11, 0, tzinfo=APP_TIMEZONE)
    assert get_attendance_status(None, None, record_date, current_dt) == "NOT_MARKED"

def test_status_absent_after_cutoff():
    # Logged In = Yes, Punch In = No, Current Time = 3:00 PM (> 2:30 PM)
    record_date = date(2026, 6, 2)
    current_dt = datetime(2026, 6, 2, 15, 0, tzinfo=APP_TIMEZONE)
    assert get_attendance_status(None, None, record_date, current_dt) == "ABSENT"

def test_status_absent_past_day():
    # Past day, no punch in
    record_date = date(2026, 6, 1)
    current_dt = datetime(2026, 6, 2, 10, 0, tzinfo=APP_TIMEZONE)
    assert get_attendance_status(None, None, record_date, current_dt) == "ABSENT"

def test_get_attendance_status_with_timeoff_no_db():
    from app.services.attendance_service import get_attendance_status_with_timeoff
    assert get_attendance_status_with_timeoff(None, 1, time(9, 0), time(18, 0), date(2026, 6, 2)) == "Present"
    assert get_attendance_status_with_timeoff(None, 1, time(9, 0), None, date(2026, 6, 2)) == "Working"
    assert get_attendance_status_with_timeoff(None, 1, None, None, date(2026, 6, 2), datetime(2026, 6, 2, 11, 0, tzinfo=APP_TIMEZONE)) == "Not Marked"
    assert get_attendance_status_with_timeoff(None, 1, None, None, date(2026, 6, 2), datetime(2026, 6, 2, 15, 0, tzinfo=APP_TIMEZONE)) == "Absent"


def test_status_grand_total_evaluation_includes_break():
    # 09:33 to 18:06: Grand total is 513 minutes (8h 33m)
    # Even though 60-min lunch leaves 453m net work, shift timing includes break,
    # so presence of 8h 33m >= 8h 0m evaluates to PRESENT.
    assert get_attendance_status(time(9, 33), time(18, 6), date(2026, 9, 7)) == "PRESENT"


def test_status_grand_total_half_day_and_absent():
    # 09:00 to 13:30 = 270 minutes (4h 30m) -> HALF_DAY (>= 240m, < 480m)
    assert get_attendance_status(time(9, 0), time(13, 30), date(2026, 6, 2)) == "HALF_DAY"

    # 09:00 to 11:00 = 120 minutes (2h 0m) -> ABSENT (< 240m)
    assert get_attendance_status(time(9, 0), time(11, 0), date(2026, 6, 2)) == "ABSENT"

