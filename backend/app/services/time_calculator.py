from datetime import time, datetime, date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from app.models.attendance import Attendance
from app.models.master_data import Shift
from app.domain.attendance.services.shift_calculation_service import ShiftCalculationService

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

# Deprecated fallback defaults kept for legacy imports
OFFICE_START_TIME = time(9, 0)
OFFICE_END_TIME = time(18, 0)
LUNCH_START_TIME = time(13, 0)
LUNCH_END_TIME = time(14, 0)
GRACE_PERIOD_MINUTES = 30
REQUIRED_WORKING_MINUTES = 480
HALF_DAY_MINUTES = 240

def _time_to_minutes(t: time) -> int:
    return ShiftCalculationService.time_to_minutes(t)

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

def calculate_late_minutes(punch_in: time, shift: Optional[Shift] = None) -> int:
    return ShiftCalculationService.calculate_late_minutes(punch_in, shift)

def calculate_early_exit_minutes(punch_out: time, shift: Optional[Shift] = None) -> int:
    return ShiftCalculationService.calculate_early_exit_minutes(punch_out, shift)

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
    timeoff_duration_hours: float = 0.0,
    shift: Optional[Shift] = None,
) -> str:
    """
    Delegates to ShiftCalculationService for dynamic status calculation.
    """
    return ShiftCalculationService.get_attendance_status(
        punch_in=punch_in,
        punch_out=punch_out,
        record_date=record_date,
        shift=shift,
        current_dt=current_dt,
        timeoff_duration_hours=timeoff_duration_hours
    )

def determine_status(punch_in: time, punch_out: time, timeoff_duration_hours: float = 0.0, shift: Optional[Shift] = None) -> str:
    """Determine the status of attendance."""
    from datetime import date
    return get_attendance_status(punch_in, punch_out, date.today(), timeoff_duration_hours=timeoff_duration_hours, shift=shift)

def calculate_attendance_flags(attendance_record: Attendance, shift: Optional[Shift] = None) -> list[str]:
    flags = []
    if attendance_record.punch_in:
        late_mins = calculate_late_minutes(attendance_record.punch_in, shift)
        if late_mins > 0:
            flags.append("LATE_ARRIVAL")
            
    if attendance_record.punch_out:
        early_mins = calculate_early_exit_minutes(attendance_record.punch_out, shift)
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
    from sqlalchemy.orm import object_session
    from app.domain.attendance.repositories.shift_repository import ShiftRepository

    db = object_session(attendance_record)
    shift = None
    if attendance_record.shift:
        shift = attendance_record.shift
    elif db is not None:
        shift = ShiftRepository.get_assigned_shift(db, attendance_record.employee_id, attendance_record.date)
        attendance_record.shift_id = shift.id

    effective_shift = ShiftCalculationService.get_effective_shift(shift)

    # Resolve approved timeoff duration from session if not passed explicitly
    if timeoff_duration_hours == 0.0:
        timeoff_duration_hours = _get_approved_timeoff_hours(attendance_record)

    if not attendance_record.punch_in:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.break_minutes = int(timeoff_duration_hours * 60)
        attendance_record.status = get_attendance_status(None, None, attendance_record.date, timeoff_duration_hours=timeoff_duration_hours, shift=effective_shift)
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
        for f in ["AUTO_CHECKOUT", "MISSED_PUNCH", "REGULARIZED"]:
            if f in attendance_record.flags:
                flags.append(f)
        attendance_record.flags = flags
        return

    in_minutes = _time_to_minutes(attendance_record.punch_in)
    out_minutes = _time_to_minutes(attendance_record.punch_out)
    start_mins = _time_to_minutes(effective_shift.start_time or time(9, 0))
    end_mins = _time_to_minutes(effective_shift.end_time or time(18, 0))

    if (effective_shift.is_night_shift or end_mins < start_mins) and out_minutes < in_minutes:
        out_minutes += 1440

    if out_minutes <= in_minutes:
        attendance_record.total_working_minutes = 0
        attendance_record.overtime_minutes = 0
        attendance_record.grand_total_minutes = 0
        attendance_record.status = "ABSENT"
        attendance_record.flags = []
        return
        
    gross_minutes = out_minutes - in_minutes
    lunch_minutes = ShiftCalculationService.calculate_lunch_overlap(attendance_record.punch_in, attendance_record.punch_out, effective_shift)
    
    timeoff_overlap_minutes = 0
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
            st = r.start_time or effective_shift.start_time or time(9, 0)
            et = r.end_time or effective_shift.end_time or time(18, 0)
            overlap = calculate_overlap_minutes(
                attendance_record.punch_in,
                attendance_record.punch_out,
                st,
                et
            )
            timeoff_overlap_minutes += overlap
    else:
        timeoff_overlap_minutes = min(gross_minutes, int(timeoff_duration_hours * 60))

    net_working_minutes = max(0, gross_minutes - lunch_minutes - timeoff_overlap_minutes)
    
    overtime_minutes = 0
    if attendance_record.overtime_approved:
        overtime_minutes = ShiftCalculationService.calculate_overtime_minutes(
            attendance_record.punch_in,
            attendance_record.punch_out,
            effective_shift,
            net_working_minutes=net_working_minutes
        )
    
    attendance_record.total_working_minutes = net_working_minutes
    attendance_record.overtime_minutes = overtime_minutes
    attendance_record.grand_total_minutes = net_working_minutes + overtime_minutes
    
    timeoff_minutes = int(timeoff_duration_hours * 60)
    attendance_record.break_minutes = lunch_minutes + timeoff_minutes
    
    attendance_record.status = get_attendance_status(
        attendance_record.punch_in,
        attendance_record.punch_out,
        attendance_record.date,
        timeoff_duration_hours=timeoff_duration_hours,
        shift=effective_shift
    )
    attendance_record.flags = calculate_attendance_flags(attendance_record, effective_shift)
