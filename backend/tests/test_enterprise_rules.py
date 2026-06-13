from datetime import time, date
from app.models.attendance import Attendance
from app.services.time_calculator import (
    calculate_times,
    calculate_late_minutes,
    calculate_early_exit_minutes,
    get_attendance_status
)

def test_enterprise_standard_present():
    # Punch In at 09:00, Punch Out at 18:00
    # Gross = 9 hours (540 mins)
    # Lunch break = 60 mins (since 09:00 < 13:00 and 18:00 > 14:00)
    # Net = 8 hours (480 mins) -> Present
    att = Attendance(
        date=date(2026, 6, 4),
        punch_in=time(9, 0),
        punch_out=time(18, 0)
    )
    calculate_times(att)
    assert att.total_working_minutes == 480
    assert att.break_minutes == 60
    assert att.overtime_minutes == 0
    assert att.status == "PRESENT"
    
    # Late arrival and early exit checks
    assert calculate_late_minutes(att.punch_in) == 0
    assert calculate_early_exit_minutes(att.punch_out) == 0

def test_enterprise_late_arrival_half_day():
    # Punch In at 11:36, Punch Out at 18:35
    # Gross = 6 hours 59 minutes (419 mins)
    # Lunch overlap = 60 mins
    # Net = 5 hours 59 minutes (359 mins) -> Half Day (>= 240, < 480)
    att = Attendance(
        date=date(2026, 6, 4),
        punch_in=time(11, 36),
        punch_out=time(18, 35)
    )
    calculate_times(att)
    assert att.total_working_minutes == 359
    assert att.break_minutes == 60
    assert att.status == "HALF_DAY"
    
    # Late: 11:36 - 09:00 = 2 hours 36 minutes (156 minutes)
    assert calculate_late_minutes(att.punch_in) == 156
    assert calculate_early_exit_minutes(att.punch_out) == 0

def test_enterprise_early_exit_half_day():
    # Punch In at 09:10, Punch Out at 17:30
    # Gross = 8 hours 20 minutes (500 mins)
    # Lunch overlap = 60 mins
    # Net = 7 hours 20 minutes (440 mins) -> Half Day
    att = Attendance(
        date=date(2026, 6, 4),
        punch_in=time(9, 10),
        punch_out=time(17, 30)
    )
    calculate_times(att)
    assert att.total_working_minutes == 440
    assert att.break_minutes == 60
    assert att.status == "HALF_DAY"
    
    # Late: 09:10 <= 09:15 -> 0 mins
    assert calculate_late_minutes(att.punch_in) == 0
    # Early Exit: 18:00 - 17:30 = 30 mins
    assert calculate_early_exit_minutes(att.punch_out) == 30

def test_enterprise_overtime():
    # Punch In at 09:00, Punch Out at 19:30
    # Gross = 10 hours 30 minutes (630 mins)
    # Lunch overlap = 60 mins
    # Net = 9 hours 30 minutes (570 mins)
    # Overtime = 570 - 480 = 90 mins (1h 30m)
    att = Attendance(
        date=date(2026, 6, 4),
        punch_in=time(9, 0),
        punch_out=time(19, 30),
        overtime_approved=True
    )
    calculate_times(att)
    assert att.total_working_minutes == 570
    assert att.overtime_minutes == 90
    assert att.status == "PRESENT"

def test_enterprise_absent():
    # Punch In at 09:00, Punch Out at 12:30
    # Gross = 3h 30m (210 mins)
    # Lunch overlap = 0 (punched out before lunch start 13:00)
    # Net = 210 mins (< 240 mins) -> Absent
    att = Attendance(
        date=date(2026, 6, 4),
        punch_in=time(9, 0),
        punch_out=time(12, 30)
    )
    calculate_times(att)
    assert att.total_working_minutes == 210
    assert att.status == "ABSENT"
