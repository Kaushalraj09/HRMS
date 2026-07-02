from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from app.models.attendance import OvertimeRequest, Attendance
from app.domain.attendance.repositories.shift_repository import ShiftRepository
from app.domain.events.dispatcher import EventDispatcher
from app.domain.events.types import OvertimeApproved
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

# Configurable defaults for maximum limits if not overridden
DEFAULT_MAX_OVERTIME_WEEKLY_MINUTES = 600   # 10 Hours
DEFAULT_MAX_OVERTIME_MONTHLY_MINUTES = 2400  # 40 Hours

class OvertimeService:
    @staticmethod
    def get_approved_overtime_minutes(db: Session, employee_id: int, attendance_id: int) -> int:
        """Get approved overtime minutes for a specific employee and attendance session."""
        req = (
            db.query(OvertimeRequest)
            .filter(
                OvertimeRequest.employee_id == employee_id,
                OvertimeRequest.attendance_id == attendance_id,
                OvertimeRequest.status == "Approved"
            )
            .first()
        )
        return req.requested_minutes if req else 0

    @staticmethod
    def create_overtime_request(
        db: Session,
        employee_id: int,
        attendance_id: int,
        requested_minutes: int,
        reason: str
    ) -> OvertimeRequest:
        """Create a new overtime request, validating shift, weekly, and monthly limits."""
        attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
        if not attendance:
            raise HTTPException(status_code=404, detail="Attendance record not found.")

        shift = ShiftRepository.get_assigned_shift(db, employee_id, attendance.date)
        
        # 1. Verify shift overtime allowance
        if not shift.overtime_allowed:
            raise HTTPException(status_code=400, detail="Overtime is not allowed for the assigned shift.")
            
        # 2. Daily Shift Limit check
        max_shift_ot = shift.max_overtime_minutes or 120
        if requested_minutes > max_shift_ot:
            raise HTTPException(
                status_code=400,
                detail=f"Requested overtime exceeds maximum shift limit of {max_shift_ot} minutes."
            )
            
        # 3. Weekly Limit check
        start_of_week = attendance.date - timedelta(days=attendance.date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        weekly_ot = (
            db.query(OvertimeRequest)
            .filter(
                OvertimeRequest.employee_id == employee_id,
                OvertimeRequest.status == "Approved",
                OvertimeRequest.attendance_id != None
            )
            .join(Attendance)
            .filter(Attendance.date.between(start_of_week, end_of_week))
            .all()
        )
        total_weekly = sum(r.requested_minutes for r in weekly_ot)
        if total_weekly + requested_minutes > DEFAULT_MAX_OVERTIME_WEEKLY_MINUTES:
            raise HTTPException(
                status_code=400,
                detail=f"Weekly overtime limit of {DEFAULT_MAX_OVERTIME_WEEKLY_MINUTES} minutes exceeded."
            )
            
        # 4. Monthly Limit check
        start_of_month = date(attendance.date.year, attendance.date.month, 1)
        if attendance.date.month == 12:
            end_of_month = date(attendance.date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(attendance.date.year, attendance.date.month + 1, 1) - timedelta(days=1)
            
        monthly_ot = (
            db.query(OvertimeRequest)
            .filter(
                OvertimeRequest.employee_id == employee_id,
                OvertimeRequest.status == "Approved",
                OvertimeRequest.attendance_id != None
            )
            .join(Attendance)
            .filter(Attendance.date.between(start_of_month, end_of_month))
            .all()
        )
        total_monthly = sum(r.requested_minutes for r in monthly_ot)
        if total_monthly + requested_minutes > DEFAULT_MAX_OVERTIME_MONTHLY_MINUTES:
            raise HTTPException(
                status_code=400,
                detail=f"Monthly overtime limit of {DEFAULT_MAX_OVERTIME_MONTHLY_MINUTES} minutes exceeded."
            )

        # Check duplicate pending/approved request
        existing = (
            db.query(OvertimeRequest)
            .filter(
                OvertimeRequest.employee_id == employee_id,
                OvertimeRequest.attendance_id == attendance_id,
                OvertimeRequest.status.in_(["Pending", "Approved"])
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="An active overtime request already exists for this record.")

        req = OvertimeRequest(
            employee_id=employee_id,
            attendance_id=attendance_id,
            requested_minutes=requested_minutes,
            reason=reason,
            status="Pending"
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        
        return req

    @staticmethod
    def approve_overtime_request(db: Session, request_id: int, approved_by_user_id: int) -> OvertimeRequest:
        """Approve an overtime request, triggering domain event and recalculating attendance metrics."""
        req = db.query(OvertimeRequest).filter(OvertimeRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Overtime request not found.")
            
        if req.status != "Pending":
            raise HTTPException(status_code=400, detail="Overtime request is not in pending status.")
            
        req.status = "Approved"
        req.approved_by = approved_by_user_id
        req.approved_at = datetime.now()
        
        # Trigger recalculation of the linked attendance metrics
        if req.attendance_id:
            attendance = db.query(Attendance).filter(Attendance.id == req.attendance_id).first()
            if attendance:
                # Recalculate using calculators
                from app.domain.attendance.calculators.shift_calculator import ShiftCalculator
                from app.domain.attendance.repositories.shift_repository import ShiftRepository
                from app.domain.attendance.policies.attendance_policy_evaluator import AttendancePolicyEvaluator
                from app.services.attendance_service import get_timeoff_duration_for_date
                
                shift = ShiftRepository.get_assigned_shift(db, attendance.employee_id, attendance.date)
                total_break, unpaid_break = ShiftCalculator.calculate_break_overlaps(
                    db, attendance.punch_in, attendance.punch_out, shift
                )
                
                timeoff_hours = get_timeoff_duration_for_date(db, attendance.employee_id, attendance.date)
                timeoff_mins = int(timeoff_hours * 60)
                
                in_mins = ShiftCalculator.time_to_minutes(attendance.punch_in)
                out_mins = ShiftCalculator.time_to_minutes(attendance.punch_out)
                gross = max(0, out_mins - in_mins)
                net = max(0, gross - unpaid_break)
                
                # Check for approved overtime minutes
                approved_ot = req.requested_minutes
                
                attendance.total_working_minutes = net
                attendance.overtime_minutes = approved_ot
                attendance.grand_total_minutes = net + approved_ot
                attendance.status = AttendancePolicyEvaluator.evaluate_status(
                    db, shift, net + timeoff_mins,
                    ShiftCalculator.calculate_late_minutes(attendance.punch_in, shift),
                    ShiftCalculator.calculate_early_exit_minutes(attendance.punch_out, shift),
                    requires_regularization=attendance.requires_regularization
                )
                
        db.commit()
        db.refresh(req)
        
        # Publish event
        EventDispatcher.dispatch(OvertimeApproved(
            employee_id=req.employee_id,
            overtime_request_id=req.id
        ))
        
        return req

    @staticmethod
    def reject_overtime_request(db: Session, request_id: int, approved_by_user_id: int) -> OvertimeRequest:
        """Reject a pending overtime request."""
        req = db.query(OvertimeRequest).filter(OvertimeRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Overtime request not found.")
            
        if req.status != "Pending":
            raise HTTPException(status_code=400, detail="Overtime request is not in pending status.")
            
        req.status = "Rejected"
        req.approved_by = approved_by_user_id
        req.approved_at = datetime.now()
        db.commit()
        db.refresh(req)
        
        return req
