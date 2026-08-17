from sqlalchemy.orm import Session
from datetime import date, time, datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.domain.attendance.repositories.shift_repository import ShiftRepository
from app.domain.attendance.calculators.shift_calculator import ShiftCalculator
from app.domain.attendance.policies.attendance_policy_evaluator import AttendancePolicyEvaluator
from app.domain.overtime.overtime_service import OvertimeService
from app.domain.events.dispatcher import EventDispatcher
from app.domain.events import types as ev_types
from app.services.attendance_service import get_timeoff_duration_for_date, log_audit_trail_sync
import logging

logger = logging.getLogger(__name__)
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

class PunchService:
    @staticmethod
    def punch_in(
        db: Session,
        employee_id: int,
        work_mode: str,
        latitude: float = None,
        longitude: float = None,
        address: str = None,
        image: str = None,
        custom_time: datetime = None
    ) -> Attendance:
        """
        Concurrency-safe punch in. Obtains a row-level lock on today's attendance record
        to prevent duplicate entries from double clicks or network retries.
        """
        current = custom_time or datetime.now(APP_TIMEZONE)
        if current.tzinfo is None:
            current = current.replace(tzinfo=APP_TIMEZONE)
        else:
            current = current.astimezone(APP_TIMEZONE)
            
        today = current.date()
        
        # 1. Start subtransaction/nested block & acquire row-level lock
        try:
            db.begin_nested()
            attendance = (
                db.query(Attendance)
                .with_for_update()
                .filter(Attendance.employee_id == employee_id, Attendance.date == today)
                .first()
            )
            
            # Prevent double punch-in
            if attendance:
                employee = db.query(Employee).filter(Employee.id == employee_id).first()
                emp_code = employee.employee_code if employee else f"{employee_id:04d}"
                
                if attendance.is_working:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "Already punched in. Please punch out first.",
                            "code": "ALREADY_PUNCHED_IN",
                            "employeeId": emp_code,
                            "punchInAddress": attendance.punch_in_address,
                            "workMode": attendance.work_mode,
                        }
                    )
                if attendance.punch_out is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "Already completed attendance for today. Multiple punches not allowed.",
                            "code": "ALREADY_PUNCHED_OUT",
                            "employeeId": emp_code,
                            "punchInTiming": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                            "punchOutTiming": attendance.punch_out.strftime("%I:%M %p") if attendance.punch_out else None,
                            "punchOutAddress": attendance.punch_out_address,
                            "workMode": attendance.work_mode,
                        }
                    )
            
            # Create or update record
            shift = ShiftRepository.get_assigned_shift(db, employee_id, today)
            
            # Prevent punching in before shift starts
            if shift and shift.start_time:
                # Format times for comparison (ignoring date)
                if current.time() < shift.start_time:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": f"Cannot punch in before your shift starts at {shift.start_time.strftime('%I:%M %p')}.",
                            "code": "TOO_EARLY",
                        }
                    )
            
            if not attendance:
                attendance = Attendance(
                    employee_id=employee_id,
                    shift_id=shift.id if shift else None,
                    date=today,
                    is_working=1,
                    work_mode=work_mode,
                    status="WORKING"
                )
                db.add(attendance)
                db.flush()
            else:
                attendance.is_working = 1
                attendance.work_mode = work_mode
                attendance.status = "WORKING"
                if not attendance.shift_id:
                    attendance.shift_id = shift.id
                
            attendance.punch_in = current.time()
            attendance.punch_in_latitude = latitude
            attendance.punch_in_longitude = longitude
            attendance.punch_in_address = address
            attendance.punch_in_image = image
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
            
        db.refresh(attendance)
        
        # Log Audit & Dispatch Domain Event
        log_audit_trail_sync(db, "PUNCH_IN", employee_id, f"Punched in via {work_mode} at {current.time()}")
        EventDispatcher.dispatch(ev_types.AttendancePunchedIn(
            employee_id=employee_id,
            attendance_id=attendance.id,
            punch_time=attendance.punch_in,
            work_mode=work_mode
        ))
        
        return attendance

    @staticmethod
    def punch_out(
        db: Session,
        employee_id: int,
        work_mode: str,
        latitude: float = None,
        longitude: float = None,
        address: str = None,
        image: str = None,
        custom_time: datetime = None
    ) -> Attendance:
        """
        Concurrency-safe punch out. Obtains row lock to prevent race conditions.
        """
        current = custom_time or datetime.now(APP_TIMEZONE)
        if current.tzinfo is None:
            current = current.replace(tzinfo=APP_TIMEZONE)
        else:
            current = current.astimezone(APP_TIMEZONE)
            
        today = current.date()
        
        try:
            db.begin_nested()
            attendance = (
                db.query(Attendance)
                .with_for_update()
                .filter(Attendance.employee_id == employee_id, Attendance.date == today)
                .first()
            )
            
            if not attendance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "No attendance found for today. Please punch in first.",
                        "code": "NO_ATTENDANCE_RECORD",
                    }
                )
                
            if attendance.punch_out is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Already punched out. Multiple punch-outs not allowed.",
                        "code": "ALREADY_PUNCHED_OUT",
                        "checkIn": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                        "checkOut": attendance.punch_out.strftime("%I:%M %p") if attendance.punch_out else None,
                        "address": attendance.punch_out_address,
                        "workMode": attendance.work_mode,
                    }
                )
                
            if not attendance.is_working:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Not working. Cannot punch out.",
                        "code": "NOT_WORKING",
                        "checkIn": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                        "workMode": attendance.work_mode,
                    }
                )
                
            attendance.punch_out = current.time()
            attendance.punch_out_latitude = latitude
            attendance.punch_out_longitude = longitude
            attendance.punch_out_address = address
            attendance.punch_out_image = image
            attendance.is_working = 0
            
            # Recalculate metrics based on shift configurations and break policies
            shift = ShiftRepository.get_assigned_shift(db, employee_id, today)
            
            total_break, unpaid_break = ShiftCalculator.calculate_break_overlaps(
                db, attendance.punch_in, attendance.punch_out, shift
            )
            
            in_mins = ShiftCalculator.time_to_minutes(attendance.punch_in)
            out_mins = ShiftCalculator.time_to_minutes(attendance.punch_out)
            
            gross = max(0, out_mins - in_mins)
            
            # Get approved time-off duration (if any)
            timeoff_hours = get_timeoff_duration_for_date(db, employee_id, today)
            timeoff_mins = int(timeoff_hours * 60)
            
            # Calculate overlap of approved timeoff with the punch duration to prevent double subtraction
            timeoff_overlap_minutes = 0
            from app.models.timeoff import TimeOffRequest
            timeoff_reqs = (
                db.query(TimeOffRequest)
                .filter(
                    TimeOffRequest.employee_id == employee_id,
                    TimeOffRequest.date == today,
                    TimeOffRequest.status.in_(["Approved", "Active", "Completed"])
                )
                .all()
            )
            for r in timeoff_reqs:
                st = r.start_time or shift.start_time
                et = r.end_time or shift.end_time
                overlap = ShiftCalculator.calculate_overlap_minutes(
                    attendance.punch_in, attendance.punch_out, st, et
                )
                timeoff_overlap_minutes += overlap
                
            net_working_minutes = max(0, gross - unpaid_break - timeoff_overlap_minutes)
            
            from app.domain.attendance.services.shift_calculation_service import ShiftCalculationService
            approved_ot_minutes = OvertimeService.get_approved_overtime_minutes(db, employee_id, attendance.id)
            if not approved_ot_minutes and attendance.overtime_approved:
                approved_ot_minutes = ShiftCalculationService.calculate_overtime_minutes(
                    attendance.punch_in,
                    attendance.punch_out,
                    shift,
                    net_working_minutes=net_working_minutes
                )
            
            attendance.total_working_minutes = net_working_minutes
            attendance.overtime_minutes = approved_ot_minutes
            attendance.grand_total_minutes = net_working_minutes + approved_ot_minutes
            attendance.break_minutes = total_break + timeoff_mins
            
            # Evaluate dynamic policy status
            late_mins = ShiftCalculator.calculate_late_minutes(attendance.punch_in, shift)
            early_mins = ShiftCalculator.calculate_early_exit_minutes(attendance.punch_out, shift)
            
            attendance.status = AttendancePolicyEvaluator.evaluate_status(
                db=db,
                shift=shift,
                credited_minutes=net_working_minutes + timeoff_mins,
                late_minutes=late_mins,
                early_exit_minutes=early_mins,
                requires_regularization=attendance.requires_regularization
            )
            
            # Build flags dynamically
            flags = []
            if late_mins > 0:
                flags.append("LATE_ARRIVAL")
            if early_mins > 0:
                flags.append("EARLY_EXIT")
            if approved_ot_minutes > 0:
                flags.append("OVERTIME")
            
            # Retain any historical tags (AUTO_CHECKOUT, etc.)
            for f in ["AUTO_CHECKOUT", "MISSED_PUNCH", "REGULARIZED"]:
                if f in attendance.flags:
                    flags.append(f)
            attendance.flags = flags
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
            
        db.refresh(attendance)
        
        # Log Audit & Dispatch Domain Event
        log_audit_trail_sync(db, "PUNCH_OUT", employee_id, f"Punched out via {work_mode} at {current.time()}")
        EventDispatcher.dispatch(ev_types.AttendancePunchedOut(
            employee_id=employee_id,
            attendance_id=attendance.id,
            punch_time=attendance.punch_out,
            work_mode=work_mode
        ))
        
        return attendance
