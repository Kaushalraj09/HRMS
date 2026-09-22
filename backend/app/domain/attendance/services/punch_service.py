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
from app.core.geofence import validate_employee_geofence, calculate_haversine_distance
from app.core.shift_rules import get_shift_rule_value
import logging
import os

logger = logging.getLogger(__name__)
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def is_test_punch_employee(employee: Employee = None, user_email: str = None) -> bool:
    """
    Check if an employee or user email is a recognized test account
    (e.g., TestVivekEmp@gmail.com, TestVivekHr@gmail.com, TestVivekAdmin@gmail.com).
    Test accounts are granted bypasses for shift windows, geofence, and multiple punch limits.
    """
    emails = set()
    if employee and employee.official_email:
        emails.add(employee.official_email.strip().lower())
    if user_email:
        emails.add(user_email.strip().lower())

    test_pattern = "testvivek"
    static_test_emails = {
        "testvivekemp@gmail.com",
        "testvivekhr@gmail.com",
        "testvivekadmin@gmail.com",
        "emp@hrms.com",
        "hr@hrms.com",
    }

    extra = os.getenv("TEST_PUNCH_BYPASS_EMAILS", "")
    if extra:
        static_test_emails.update(e.strip().lower() for e in extra.split(",") if e.strip())

    for e in emails:
        if e in static_test_emails or e.startswith(test_pattern):
            return True

    return False


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
            
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found")

            emp_code = employee.employee_code if employee else f"{employee_id:04d}"
            is_test_user = is_test_punch_employee(employee)

            # Prevent double punch-in (Bypassed for test accounts)
            if attendance:
                if attendance.is_working and not is_test_user:
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
                if attendance.punch_out is not None and not is_test_user:
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

                # If test user previously punched out, reset punch_out to allow punching in multiple times
                if is_test_user and attendance.punch_out is not None:
                    attendance.punch_out = None
                    attendance.punch_out_latitude = None
                    attendance.punch_out_longitude = None
                    attendance.punch_out_address = None
                    attendance.punch_out_image = None
                    attendance.is_working = 1
                    attendance.status = "WORKING"

            # Geofence & remote validation
            emp_loc = (employee.work_location or "").strip().lower()
            is_remote_employee = not emp_loc or "remote" in emp_loc or emp_loc in ["wfh", "hybrid"] or is_test_user
            if not is_remote_employee:
                from app.models.master_data import WorkLocation
                from sqlalchemy import func
                wl = db.query(WorkLocation).filter(
                    (func.lower(WorkLocation.name) == emp_loc) | (func.lower(WorkLocation.code) == emp_loc)
                ).first()
                if wl and wl.location_type and wl.location_type.lower() != "office":
                    is_remote_employee = True

            req_mode = (work_mode or "").strip().lower()
            if not is_test_user and req_mode in ["remote", "work from home", "wfh", "field"] and not is_remote_employee:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "message": f"Assigned work location '{employee.work_location}' requires on-site attendance. Remote mode is not permitted.",
                        "office": employee.work_location,
                    }
                )

            # Anti-spoofing: Check for impossible travel speed (> 250 km/h) if recent punch exists within 2 hours
            if not is_test_user and latitude is not None and longitude is not None:
                last_record = db.query(Attendance).filter(
                    Attendance.employee_id == employee_id,
                    Attendance.date <= today
                ).order_by(Attendance.date.desc(), Attendance.id.desc()).first()

                if last_record:
                    last_time = None
                    last_lat = None
                    last_lon = None
                    if last_record.punch_out and last_record.punch_out_latitude is not None and last_record.punch_out_longitude is not None:
                        last_time = datetime.combine(last_record.date, last_record.punch_out)
                        last_lat = last_record.punch_out_latitude
                        last_lon = last_record.punch_out_longitude
                    elif last_record.punch_in and last_record.punch_in_latitude is not None and last_record.punch_in_longitude is not None:
                        last_time = datetime.combine(last_record.date, last_record.punch_in)
                        last_lat = last_record.punch_in_latitude
                        last_lon = last_record.punch_in_longitude

                    if last_time and last_lat is not None and last_lon is not None:
                        now_dt = datetime.combine(today, current.time())
                        if now_dt > last_time:
                            elapsed_hours = (now_dt - last_time).total_seconds() / 3600.0
                            if 0 < elapsed_hours < 2.0:
                                dist_meters = calculate_haversine_distance(last_lat, last_lon, float(latitude), float(longitude))
                                speed_kmh = (dist_meters / 1000.0) / elapsed_hours
                                if speed_kmh > 250.0:
                                    raise HTTPException(
                                        status_code=status.HTTP_400_BAD_REQUEST,
                                        detail={
                                            "success": False,
                                            "message": f"Impossible travel detected: calculated speed of {round(speed_kmh, 1)} km/h between punches exceeds allowed limit (250 km/h). Please verify your GPS location.",
                                            "speed_kmh": round(speed_kmh, 1)
                                        }
                                    )

            effective_work_mode = "Remote" if is_remote_employee else "Office"
            try:
                geofence_data = validate_employee_geofence(
                    db, employee, latitude, longitude, work_mode=effective_work_mode
                )
            except Exception:
                if is_test_user:
                    geofence_data = {
                        "distance_meters": 0,
                        "work_location_id": None,
                        "work_location_name": "Test Office"
                    }
                else:
                    raise
            
            # Create or update record
            shift = ShiftRepository.get_assigned_shift(db, employee_id, today)
            
            # Apply early punch-in logic if shift is configured (Bypassed for test accounts)
            if not is_test_user and shift and shift.start_time:
                shift_start_dt = datetime.combine(today, shift.start_time)
                current_dt = datetime.combine(today, current.time())
                
                # If punching in before shift start
                if current_dt < shift_start_dt:
                    time_diff = shift_start_dt - current_dt
                    minutes_early = int(time_diff.total_seconds() / 60)
                    
                    allow_early = get_shift_rule_value(shift, "allow_early_punch_in")
                    early_window = get_shift_rule_value(shift, "early_coming_minutes")
                    
                    if not allow_early and minutes_early > 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "message": f"Cannot punch in before your shift starts at {shift.start_time.strftime('%I:%M %p')}.",
                                "code": "EARLY_PUNCH_NOT_ALLOWED"
                            }
                        )
                        
                    if minutes_early > early_window:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "message": f"Cannot punch in yet. Early punch-in is allowed only {early_window} minutes before your shift starts at {shift.start_time.strftime('%I:%M %p')}.",
                                "code": "OUTSIDE_EARLY_PUNCH_WINDOW"
                            }
                        )
            
            if not attendance:
                attendance = Attendance(
                    employee_id=employee_id,
                    date=today,
                    is_working=1,
                    work_mode=effective_work_mode,
                    status="WORKING"
                )
                if shift:
                    attendance.shift_id = shift.id
                    attendance.scheduled_start = shift.start_time
                    attendance.scheduled_end = shift.end_time
                    attendance.punch_in_grace_minutes = get_shift_rule_value(shift, "punch_in_grace_minutes")
                    attendance.early_punch_window_minutes = get_shift_rule_value(shift, "early_coming_minutes")
                    attendance.shift_grace_minutes = get_shift_rule_value(shift, "shift_grace_minutes")
                db.add(attendance)
                db.flush()
            else:
                attendance.is_working = 1
                attendance.work_mode = effective_work_mode
                attendance.status = "WORKING"
                if shift and not attendance.shift_id:
                    attendance.shift_id = shift.id
                    attendance.scheduled_start = shift.start_time
                    attendance.scheduled_end = shift.end_time
                    attendance.punch_in_grace_minutes = get_shift_rule_value(shift, "punch_in_grace_minutes")
                    attendance.early_punch_window_minutes = get_shift_rule_value(shift, "early_coming_minutes")
                    attendance.shift_grace_minutes = get_shift_rule_value(shift, "shift_grace_minutes")
                
            attendance.punch_in = current.time()
            attendance.punch_in_latitude = latitude
            attendance.punch_in_longitude = longitude
            attendance.punch_in_address = address
            attendance.punch_in_image = image
            attendance.work_location_id = geofence_data.get("work_location_id")
            attendance.work_location_name = geofence_data.get("work_location_name")
            attendance.geofence_distance_meters = geofence_data.get("distance_meters")

            # Calculate Early Arrival & Late constraints
            if shift and shift.start_time:
                shift_start_dt = datetime.combine(today, shift.start_time)
                current_dt = datetime.combine(today, current.time())
                grace_mins = get_shift_rule_value(attendance, "punch_in_grace_minutes")
                
                # Calculate credited start
                if current_dt < shift_start_dt:
                    time_diff = shift_start_dt - current_dt
                    minutes_early = int(time_diff.total_seconds() / 60)
                    attendance.early_arrival_minutes = minutes_early
                    attendance.early_approval_status = "Approved"
                    attendance.late_minutes = 0
                    attendance.credited_work_start = shift.start_time
                    attendance.status = "WORKING"
                else:
                    attendance.early_arrival_minutes = 0
                    attendance.credited_work_start = current.time()
                    time_diff = current_dt - shift_start_dt
                    minutes_late = int(time_diff.total_seconds() / 60)
                    
                    if minutes_late <= grace_mins:
                        attendance.late_minutes = 0
                        attendance.status = "WORKING"
                    else:
                        attendance.late_minutes = minutes_late
                        attendance.status = "LATE"
            else:
                attendance.credited_work_start = current.time()
            
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
            
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found")

            is_test_user = is_test_punch_employee(employee)

            if not attendance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "No attendance found for today. Please punch in first.",
                        "code": "NO_ATTENDANCE_RECORD",
                    }
                )
                
            if attendance.punch_out is not None and not is_test_user:
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
                
            if not attendance.is_working and not is_test_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Not working. Cannot punch out.",
                        "code": "NOT_WORKING",
                        "checkIn": attendance.punch_in.strftime("%I:%M %p") if attendance.punch_in else None,
                        "workMode": attendance.work_mode,
                    }
                )

            # Office worker punch-out geofence validation against master data
            emp_loc = (employee.work_location or "").strip().lower()
            is_remote_employee = not emp_loc or "remote" in emp_loc or emp_loc in ["wfh", "hybrid"] or is_test_user
            if not is_remote_employee:
                from app.models.master_data import WorkLocation
                from sqlalchemy import func
                wl = db.query(WorkLocation).filter(
                    (func.lower(WorkLocation.name) == emp_loc) | (func.lower(WorkLocation.code) == emp_loc)
                ).first()
                if wl and wl.location_type and wl.location_type.lower() != "office":
                    is_remote_employee = True

            req_mode = (work_mode or attendance.work_mode or "").strip().lower()
            if not is_test_user and req_mode in ["remote", "work from home", "wfh", "field"] and not is_remote_employee:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "message": f"Assigned work location '{employee.work_location}' requires on-site attendance. Remote mode is not permitted.",
                        "office": employee.work_location,
                    }
                )

            # Anti-spoofing: Check for impossible travel speed (> 250 km/h) between punch-in and punch-out
            if not is_test_user and latitude is not None and longitude is not None and attendance.punch_in and attendance.punch_in_latitude is not None and attendance.punch_in_longitude is not None:
                punch_in_dt = datetime.combine(today, attendance.punch_in)
                now_dt = datetime.combine(today, current.time())
                if now_dt > punch_in_dt:
                    elapsed_hours = (now_dt - punch_in_dt).total_seconds() / 3600.0
                    if 0 < elapsed_hours < 2.0:
                        dist_meters = calculate_haversine_distance(
                            attendance.punch_in_latitude, attendance.punch_in_longitude,
                            float(latitude), float(longitude)
                        )
                        speed_kmh = (dist_meters / 1000.0) / elapsed_hours
                        if speed_kmh > 250.0:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail={
                                    "success": False,
                                    "message": f"Impossible travel detected: calculated speed of {round(speed_kmh, 1)} km/h between punches exceeds allowed limit (250 km/h). Please verify your GPS location.",
                                    "speed_kmh": round(speed_kmh, 1)
                                }
                            )

            effective_work_mode = "Remote" if is_remote_employee else "Office"
            try:
                geofence_data = validate_employee_geofence(db, employee, latitude, longitude, work_mode=effective_work_mode)
            except Exception:
                if is_test_user:
                    geofence_data = {
                        "distance_meters": 0,
                        "work_location_id": None,
                        "work_location_name": "Test Office"
                    }
                else:
                    raise

            attendance.work_mode = effective_work_mode

            attendance.punch_out = current.time()
            attendance.punch_out_latitude = latitude
            attendance.punch_out_longitude = longitude
            attendance.punch_out_address = address
            attendance.punch_out_image = image
            attendance.is_working = 0
            if geofence_data.get("work_location_id") and not attendance.work_location_id:
                attendance.work_location_id = geofence_data.get("work_location_id")
                attendance.work_location_name = geofence_data.get("work_location_name")
            
            # Recalculate metrics based on shift configurations and break policies
            shift = ShiftRepository.get_assigned_shift(db, employee_id, today)
            
            total_break, unpaid_break = ShiftCalculator.calculate_break_overlaps(
                db, attendance.punch_in, attendance.punch_out, shift
            )
            
            in_mins = ShiftCalculator.time_to_minutes(attendance.punch_in)
            out_mins = ShiftCalculator.time_to_minutes(attendance.punch_out)
            start_mins = ShiftCalculator.time_to_minutes(shift.start_time or time(9, 0)) if shift else 540
            effective_in_mins = in_mins
            if shift and not shift.is_night_shift and in_mins < start_mins:
                effective_in_mins = start_mins

            if out_mins < in_mins:
                out_mins += 1440
            
            gross = max(0, out_mins - effective_in_mins)
            
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
                    net_working_minutes=net_working_minutes,
                    is_extended=bool(attendance.overtime_extended)
                )
            
            attendance.total_working_minutes = net_working_minutes
            attendance.regular_work_minutes = max(0, net_working_minutes - approved_ot_minutes) if approved_ot_minutes > 0 else net_working_minutes
            attendance.overtime_minutes = approved_ot_minutes
            attendance.break_minutes = total_break + timeoff_mins
            attendance.grand_total_minutes = net_working_minutes + total_break
            
            # Evaluate dynamic policy status using overall shift duration grace
            late_mins = ShiftCalculator.calculate_late_minutes(attendance.punch_in, shift)
            
            req_work_mins = (shift.required_work_minutes or int(float(shift.working_hours or 8.0) * 60)) if shift else 480
            shift_grace = get_shift_rule_value(shift, "shift_grace_minutes") if shift else 15
            effective_required_mins = max(0, req_work_mins - shift_grace)
            
            credited_total = net_working_minutes + timeoff_mins
            if credited_total >= effective_required_mins:
                early_mins = 0
            else:
                early_mins = effective_required_mins - credited_total
            
            attendance.status = AttendancePolicyEvaluator.evaluate_status(
                db=db,
                shift=shift,
                credited_minutes=credited_total,
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
