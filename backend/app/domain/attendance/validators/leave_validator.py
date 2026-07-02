from sqlalchemy.orm import Session
from datetime import date, time, datetime
from app.models.timeoff import TimeOffRequest
from app.models.attendance import AttendanceRegularizationRequest, OvertimeRequest, Attendance
from app.models.master_data import Holiday
from app.domain.attendance.repositories.shift_repository import ShiftRepository
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class LeaveValidator:
    @staticmethod
    def _time_to_minutes(t: time) -> int:
        if not t:
            return 0
        return t.hour * 60 + t.minute

    @staticmethod
    def _ranges_overlap(s1: time, e1: time, s2: time, e2: time) -> bool:
        """Check if two time intervals overlap (strictly overlap)."""
        if not s1 or not e1 or not s2 or not e2:
            return False
        m_s1 = LeaveValidator._time_to_minutes(s1)
        m_e1 = LeaveValidator._time_to_minutes(e1)
        m_s2 = LeaveValidator._time_to_minutes(s2)
        m_e2 = LeaveValidator._time_to_minutes(e2)
        
        return max(m_s1, m_s2) < min(m_e1, m_e2)

    @staticmethod
    def validate_leave(db: Session, employee_id: int, target_date: date, start_time: time, end_time: time) -> None:
        """
        Validate if the requested leave interval is free from overlaps and bounds violations.
        """
        if start_time is None or end_time is None:
            # Full day defaults to standard shift bounds, which is validated.
            return

        # 1. Enforce shift bounds constraint
        shift = ShiftRepository.get_assigned_shift(db, employee_id, target_date)
        if shift.start_time and shift.end_time:
            if start_time < shift.start_time or end_time > shift.end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Requested time off falls outside of your assigned shift hours ({shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')})."
                )

        # 2. Prevent leave on holidays
        holiday = db.query(Holiday).filter(Holiday.holiday_date == target_date, Holiday.is_active == True).first()
        if holiday:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot apply for time off on a public holiday ({holiday.name})."
            )

        # 3. Prevent leave on weekly off (weekends)
        if target_date.weekday() in (5, 6): # Sat, Sun
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time off cannot be requested on a weekly off day."
            )

        # 4. Check for overlapping approved/pending leaves
        existing_leaves = (
            db.query(TimeOffRequest)
            .filter(
                TimeOffRequest.employee_id == employee_id,
                TimeOffRequest.date == target_date,
                TimeOffRequest.status.in_(["Pending", "Approved", "Active"])
            )
            .all()
        )
        for req in existing_leaves:
            if req.start_time and req.end_time:
                if LeaveValidator._ranges_overlap(start_time, end_time, req.start_time, req.end_time):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Overlapping time off request already exists for this slot ({req.start_time.strftime('%H:%M')} - {req.end_time.strftime('%H:%M')})."
                    )

        # 5. Check for overlapping regularization requests
        regs = (
            db.query(AttendanceRegularizationRequest)
            .filter(
                AttendanceRegularizationRequest.employee_id == employee_id,
                AttendanceRegularizationRequest.attendance_date == target_date,
                AttendanceRegularizationRequest.status.in_(["pending", "approved"])
            )
            .all()
        )
        for r in regs:
            # If they regularized punches, they can't take leave during that punch interval
            s_time = r.requested_punch_in or r.corrected_time
            e_time = r.requested_punch_out or r.corrected_time
            if s_time and e_time:
                if LeaveValidator._ranges_overlap(start_time, end_time, s_time, e_time):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Overlapping attendance regularization request already exists for this slot."
                    )

        # 6. Check for overlapping overtime requests
        overtimes = (
            db.query(OvertimeRequest)
            .filter(
                OvertimeRequest.employee_id == employee_id,
                OvertimeRequest.status.in_(["Pending", "Approved"])
            )
            .join(Attendance)
            .filter(Attendance.date == target_date)
            .all()
        )
        for ot in overtimes:
            # Overtime typically begins at shift end
            ot_start = shift.end_time or time(18, 0)
            ot_mins = ot.requested_minutes
            ot_end_mins = LeaveValidator._time_to_minutes(ot_start) + ot_mins
            ot_end = time(ot_end_mins // 60 % 24, ot_end_mins % 60)
            
            if LeaveValidator._ranges_overlap(start_time, end_time, ot_start, ot_end):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Time off request overlaps with an approved/pending overtime session."
                )
