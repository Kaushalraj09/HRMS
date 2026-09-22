from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Tuple
from datetime import date, datetime
from datetime import time as time_type
from fastapi import HTTPException, status
from app.models.timeoff import TimeOffRequest
from app.models.employee import Employee
from app.models.approval_log import ApprovalLog
from app.schemas.timeoff import TimeOffRequestCreate, TimeOffApplyPayload
from app.services.attendance_service import (
    get_timeoff_duration_for_date,
    get_today_state,
)
from app.domain.attendance.repositories.shift_repository import ShiftRepository
from app.domain.attendance.services.shift_calculation_service import ShiftCalculationService


def get_employee_leave_balances(db: Session, employee_id: int, year: int = None):
    """
    Calculate leave balances dynamically from yearly EmployeeLeaveBalance master quotas and requests.
    Returns standard categories and the full yearlyBalances breakdown.
    """
    from app.services.leave_balance_service import LeaveBalanceService
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return {}

    current_year = year or date.today().year
    yearly_list = LeaveBalanceService.get_employee_balances_summary(db, employee_id, current_year)

    # Extract quotas & balances from yearly_list for standard CL, SL, EL
    cl_item = next((item for item in yearly_list if item["code"] == "CL" or "casual" in item["name"].lower()), None)
    sl_item = next((item for item in yearly_list if item["code"] == "SL" or "sick" in item["name"].lower()), None)
    el_item = next((item for item in yearly_list if item["code"] in ("EL", "PL") or "earned" in item["name"].lower()), None)

    cl_quota = int(round(cl_item["allocated_days"])) if cl_item else 12
    cl_used = int(round(cl_item["used_days"])) if cl_item else 0
    cl_avail = int(round(cl_item["available_days"])) if cl_item else cl_quota

    sl_quota = int(round(sl_item["allocated_days"])) if sl_item else 8
    sl_used = int(round(sl_item["used_days"])) if sl_item else 0
    sl_avail = int(round(sl_item["available_days"])) if sl_item else sl_quota

    el_quota = int(round(el_item["allocated_days"])) if el_item else 18
    el_used = int(round(el_item["used_days"])) if el_item else 0
    el_avail = int(round(el_item["available_days"])) if el_item else el_quota

    total_avail = int(round(cl_avail + sl_avail + el_avail))

    return {
        "casual": {
            "quotaDays": cl_quota,
            "usedDays": cl_used,
            "availableDays": cl_avail,
        },
        "sick": {
            "quotaDays": sl_quota,
            "usedDays": sl_used,
            "availableDays": sl_avail,
        },
        "earned": {
            "quotaDays": el_quota,
            "usedDays": el_used,
            "availableDays": el_avail,
        },
        "totalAvailableDays": total_avail,
        "timeoffBalanceHours": float(employee.timeoff_balance_hours) if employee.timeoff_balance_hours is not None else 80.0,
        "yearlyBalances": yearly_list
    }

def get_timeoff_by_date(db: Session, employee_id: int, target_date: date):
    return db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id,
        TimeOffRequest.date == target_date,
        TimeOffRequest.status.in_(["Approved", "Active", "Completed"])
    ).first()

def request_timeoff(db: Session, employee_id: int, request: TimeOffRequestCreate, dispatch_event: bool = True):
    # Removed same-day working requirement to allow sick leaves and full-day same-day requests.

    shift = ShiftRepository.get_assigned_shift(db, employee_id, request.date)
    eff_shift = ShiftCalculationService.get_effective_shift(shift)
    shift_start = eff_shift.start_time or time_type(9, 0)
    shift_end = eff_shift.end_time or time_type(18, 0)
    total_shift_working_hours = float(eff_shift.working_hours or 9.0)
    
    st = request.start_time
    et = request.end_time

    lt_clean = (request.leave_type or "").strip()
    lt_lower = lt_clean.lower().replace("-", " ").replace("_", " ")

    from app.services.leave_balance_service import LeaveBalanceService
    matched_lt = LeaveBalanceService.resolve_leave_type(db, request.leave_type)

    if lt_lower in ("hourly", "hour") or (matched_lt and (matched_lt.unit_type or "").lower() == "hourly"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hourly time off is no longer supported. Please request a Half-Day or Full-Day leave."
        )

    if (matched_lt and (matched_lt.code == "WFH" or "wfh" in matched_lt.name.lower() or "work from home" in matched_lt.name.lower())) or "wfh" in lt_lower or "work from home" in lt_lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work From Home (WFH) is not a leave category."
        )

    if matched_lt:
        unit = (matched_lt.unit_type or "").lower()
        is_half_day = unit == "half_day" or "half" in matched_lt.name.lower() or matched_lt.code.upper() == "HD"
        is_full_day = not is_half_day
    else:
        is_half_day = lt_clean in ("Half-Day", "Half Day") or "half" in lt_lower
        is_full_day = not is_half_day

    if is_half_day:
        half_day_hours = float(eff_shift.half_day_hours or (total_shift_working_hours / 2.0) or 4.0)
        duration_hours = half_day_hours
        days_requested = 0.5
        lunch_start, lunch_end = ShiftCalculationService.calculate_lunch_window(eff_shift)
        # Use provided times if any, otherwise fallback to first half
        if st is None or et is None:
            st = shift_start
            et = lunch_start
        else:
            day_val = request.date
            start_dt = datetime.combine(day_val, st)
            end_dt = datetime.combine(day_val, et)
            session_dur = (end_dt - start_dt).total_seconds() / 3600.0

            is_first_half = (st == shift_start and (et == lunch_start or abs(session_dur - half_day_hours) <= 0.5))
            is_second_half = (et == shift_end and (st == lunch_end or abs(session_dur - half_day_hours) <= 0.5))
            is_legacy = (st.hour == 9 and st.minute == 0 and et.hour == 13 and et.minute == 0) or \
                        (st.hour == 14 and st.minute == 0 and et.hour == 18 and et.minute == 0)

            if not (is_first_half or is_second_half or is_legacy):
                first_half_str = f"{shift_start.strftime('%I:%M %p')} - {lunch_start.strftime('%I:%M %p')}"
                second_half_str = f"{lunch_end.strftime('%I:%M %p')} - {shift_end.strftime('%I:%M %p')}"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Half-day time-off must match your shift session: First Half ({first_half_str}) or Second Half ({second_half_str})."
                )
    else:
        duration_hours = total_shift_working_hours
        days_requested = 1.0
        if st is None:
            st = shift_start
        if et is None:
            et = shift_end

    if duration_hours < 0.5 or duration_hours > total_shift_working_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested time should be between 30 minutes (0.5 hrs) and {total_shift_working_hours:.0f} hours."
        )

    # Prevent requesting more than remaining shift balance for today.
    if request.date == date.today():
        today_state = get_today_state(db, employee_id)
        remaining_hours = float(today_state["remainingSeconds"]) / 3600.0
        if duration_hours > remaining_hours + 1e-6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested hours exceed remaining shift balance ({remaining_hours:.2f} h left).",
            )

    # Policy and overlap validation checks
    from app.domain.attendance.validators.leave_validator import LeaveValidator
    LeaveValidator.validate_leave(db, employee_id, request.date, st, et)

    existing = db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id,
        TimeOffRequest.date == request.date,
        TimeOffRequest.status != "Rejected"
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A time-off request already exists for this date."
        )

    # Reserve pending leave balance in LeaveBalanceService
    LeaveBalanceService.reserve_pending_balance(
        db=db,
        employee_id=employee_id,
        leave_type_identifier=request.leave_type,
        year=request.date.year,
        days=days_requested
    )
        
    start_date_val = request.start_date or request.date
    end_date_val = request.end_date or request.date
    total_days_val = request.total_days or days_requested

    new_request = TimeOffRequest(
        employee_id=employee_id,
        date=request.date,
        leave_type=request.leave_type,
        start_time=st,
        end_time=et,
        duration_hours=duration_hours,
        status="Pending",
        reason=request.reason,
        attachment_name=request.attachment_name,
        batch_id=request.batch_id,
        start_date=start_date_val,
        end_date=end_date_val,
        total_days=total_days_val
    )
    
    db.add(new_request)

    # Create the approval task in the same transaction as the request. A task
    # creation failure must not leave an orphaned Pending request.
    try:
        db.flush()
        from app.services.approval_service import create_approval_task
        employee_obj = db.query(Employee).filter(Employee.id == employee_id).first()
        submitted_by = employee_obj.user_id if employee_obj else 1
        create_approval_task(db, request_type="timeoff", request_id=new_request.id, employee_id=employee_id, submitted_by=submitted_by)
        db.commit()
        db.refresh(new_request)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create the approval workflow") from e

    try:
        from app.services.dashboard_service import invalidate_dashboard_cache
        invalidate_dashboard_cache(db, keys=["dashboard:admin", "dashboard:hr"])
    except Exception:
        pass
        
    # Dispatch LeaveRequested domain event
    if dispatch_event:
        try:
            from app.domain.events.dispatcher import EventDispatcher
            from app.domain.events.types import LeaveRequested
            EventDispatcher.dispatch(LeaveRequested(
                employee_id=employee_id,
                leave_request_id=new_request.id,
                date=new_request.date,
                leave_type=new_request.leave_type
            ))
        except Exception as e:
            print(f"Failed to dispatch LeaveRequested event: {e}")
        
    # Add employee_name and employee_code to the response object
    resp = new_request
    resp.employee_name = f"{new_request.employee.first_name} {new_request.employee.last_name}"
    resp.employee_code = new_request.employee.employee_code
    return resp

def get_my_timeoffs(db: Session, employee_id: int):
    results = db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id
    ).order_by(TimeOffRequest.date.desc()).all()
    
    for r in results:
        r.employee_name = f"{r.employee.first_name} {r.employee.last_name}"
        r.employee_code = r.employee.employee_code
    return results

def get_pending_requests(db: Session):
    results = db.query(TimeOffRequest).filter(
        TimeOffRequest.status == "Pending"
    ).order_by(TimeOffRequest.created_at.desc()).all()
    
    for r in results:
        r.employee_name = f"{r.employee.first_name} {r.employee.last_name}"
        r.employee_code = r.employee.employee_code
    return results

def get_processed_requests(db: Session, limit: int = 20):
    results = db.query(TimeOffRequest).filter(
        TimeOffRequest.status != "Pending"
    ).order_by(TimeOffRequest.updated_at.desc()).limit(limit).all()
    
    for r in results:
        r.employee_name = f"{r.employee.first_name} {r.employee.last_name}"
        r.employee_code = r.employee.employee_code
    return results

def approve_request(
    db: Session,
    request_id: int,
    action: str,
    admin_user_id: int,
    comments: str = None,
    approved_duration_hours: float = None,
    enforce_approval_stage: bool = True,
):
    req = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    
    if req.status != "Pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending requests can be processed.")

    if enforce_approval_stage:
        from app.services.approval_service import require_hr_stage
        require_hr_stage(db, "timeoff", request_id, admin_user_id)
        
    if action.upper() == "APPROVE":
        employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
        
        # Override duration if custom/partial approval is provided
        if approved_duration_hours is not None:
            if approved_duration_hours <= 0 or approved_duration_hours > 24:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approved duration must be > 0 and <= 24.")
            req.duration_hours = approved_duration_hours
            
        current_balance = employee.timeoff_balance_hours if employee.timeoff_balance_hours is not None else 80.0
        if current_balance < req.duration_hours:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient time-off balance.")
            
        employee.timeoff_balance_hours = current_balance - req.duration_hours
        req.status = "Approved"

        # Update yearly balances: transfer pending to used
        from app.services.leave_balance_service import LeaveBalanceService
        req_days = (req.duration_hours / 8.0) if req.duration_hours and req.duration_hours > 0 else 1.0
        LeaveBalanceService.consume_approved_balance(
            db=db,
            employee_id=req.employee_id,
            leave_type_identifier=req.leave_type,
            year=req.date.year,
            days=req_days
        )
    elif action.upper() == "REJECT":
        req.status = "Rejected"
        # Release yearly pending balance
        from app.services.leave_balance_service import LeaveBalanceService
        req_days = (req.duration_hours / 8.0) if req.duration_hours and req.duration_hours > 0 else 1.0
        LeaveBalanceService.release_rejected_balance(
            db=db,
            employee_id=req.employee_id,
            leave_type_identifier=req.leave_type,
            year=req.date.year,
            days=req_days
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action. Use APPROVE or REJECT.")

    # Update matching ApprovalTask status if pending
    try:
        from app.models.approval_task import ApprovalTask
        task = db.query(ApprovalTask).filter(
            ApprovalTask.request_type == "timeoff",
            ApprovalTask.request_id == req.id,
            ApprovalTask.status == "pending"
        ).first()
        if task:
            task.status = "approved" if action.upper() == "APPROVE" else "rejected"
            task.reviewed_by = admin_user_id
            task.reviewed_at = datetime.now()
            task.decision_comment = comments
    except Exception as e:
        print(f"Failed to synchronize approval task: {e}")

    log = ApprovalLog(
        timeoff_request_id=req.id,
        action_by_user_id=admin_user_id,
        action=action.upper(),
        comments=comments
    )
    db.add(log)
    db.commit()
    db.refresh(req)
    
    try:
        from app.services.dashboard_service import invalidate_dashboard_cache
        invalidate_dashboard_cache(db, keys=["dashboard:admin", "dashboard:hr"])
    except Exception:
        pass
    
    # Dispatch LeaveApproved or LeaveRejected domain event
    try:
        from app.domain.events.dispatcher import EventDispatcher
        from app.domain.events.types import LeaveApproved, LeaveRejected
        if action.upper() == "APPROVE":
            EventDispatcher.dispatch(LeaveApproved(
                employee_id=req.employee_id,
                leave_request_id=req.id,
                date=req.date,
                leave_type=req.leave_type,
                action_by_user_id=admin_user_id
            ))
        else:
            EventDispatcher.dispatch(LeaveRejected(
                employee_id=req.employee_id,
                leave_request_id=req.id,
                date=req.date,
                action_by_user_id=admin_user_id
            ))
    except Exception as e:
        print(f"Failed to dispatch approve/reject leave event: {e}")

    req.employee_name = f"{req.employee.first_name} {req.employee.last_name}"
    req.employee_code = req.employee.employee_code
    return req

def _duration_hours_between(start: time_type, end: time_type, day: date) -> float:
    start_dt = datetime.combine(day, start)
    end_dt = datetime.combine(day, end)
    delta = (end_dt - start_dt).total_seconds() / 3600.0
    return float(delta)

def apply_time_off(db: Session, employee_id: int, payload: TimeOffApplyPayload) -> Tuple[TimeOffRequest, float, float, int, int]:
    """
    Validates shift bounds (09:00–18:00), quota (9h / day), 30-minute slots for hourly,
    auto-approves, returns (row, approved_hours_today, remaining_hours_today).
    """
    if payload.date == date.today():
        today_state = get_today_state(db, employee_id)
        if not today_state["isWorking"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time off can only be applied while you are working."
            )

    if payload.date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot request time off for a past date.",
        )

    from app.domain.attendance.repositories.shift_repository import ShiftRepository
    from app.domain.attendance.services.shift_calculation_service import ShiftCalculationService
    shift = ShiftRepository.get_assigned_shift(db, employee_id, payload.date)
    eff_shift = ShiftCalculationService.get_effective_shift(shift)
    total_shift_working_hours = float(eff_shift.working_hours or 9.0)

    lt_raw = (payload.leave_type or "").strip()
    lt = lt_raw.lower().replace(" ", "")
    shift_start = eff_shift.start_time or time_type(9, 0)
    shift_end = eff_shift.end_time or time_type(18, 0)

    from app.models.master_data import LeaveType
    matched_lt = db.query(LeaveType).filter(
        (func.lower(LeaveType.name) == lt_raw.lower()) |
        (func.lower(LeaveType.code) == lt_raw.lower())
    ).first()

    if matched_lt:
        unit = (matched_lt.unit_type or "").lower()
        if unit == "half_day" or "half" in matched_lt.name.lower() or matched_lt.code.upper() == "HD":
            lt = "halfday"
            leave_store = matched_lt.name
        else:
            lt = "fullday"
            leave_store = matched_lt.name
    elif lt in ("fullday", "full-day"):
        leave_store = "Full-Day"
        st = shift_start
        et = shift_end
        requested = total_shift_working_hours
    elif lt in ("halfday", "half-day"):
        leave_store = "Half-Day"
        half_day_hours = float(eff_shift.half_day_hours or (total_shift_working_hours / 2.0) or 4.0)
        lunch_start, lunch_end = ShiftCalculationService.calculate_lunch_window(eff_shift)

        st = payload.start_time
        et = payload.end_time
        if st is None or et is None:
            st = shift_start
            et = lunch_start

        # First half: starts at shift start, ends at lunch start (or ~half_day_hours duration)
        is_first_half = (st == shift_start and (et == lunch_start or abs(_duration_hours_between(st, et, payload.date) - half_day_hours) <= 0.5))
        # Second half: starts at lunch end, ends at shift end (or ~half_day_hours duration)
        is_second_half = (et == shift_end and (st == lunch_end or abs(_duration_hours_between(st, et, payload.date) - half_day_hours) <= 0.5))
        # Legacy fallback for standard 9-1 and 2-6
        is_legacy = (st.hour == 9 and st.minute == 0 and et.hour == 13 and et.minute == 0) or \
                    (st.hour == 14 and st.minute == 0 and et.hour == 18 and et.minute == 0)

        if not (is_first_half or is_second_half or is_legacy):
            first_half_str = f"{shift_start.strftime('%I:%M %p')} - {lunch_start.strftime('%I:%M %p')}"
            second_half_str = f"{lunch_end.strftime('%I:%M %p')} - {shift_end.strftime('%I:%M %p')}"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Half-day session must be either First Half ({first_half_str}) or Second Half ({second_half_str}).",
            )
        requested = half_day_hours
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="leave_type must be 'Half Day' or 'Full Day'.",
        )

    approved_so_far = get_timeoff_duration_for_date(db, employee_id, payload.date)
    remaining_hours = max(0.0, total_shift_working_hours - approved_so_far)

    if requested > remaining_hours + 1e-6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested hours exceed remaining shift balance ({remaining_hours:.2f} h left).",
        )

    if payload.date == date.today():
        now = datetime.now()
        start_combined = datetime.combine(payload.date, st)
        if start_combined < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For today, start time must be at or after the current time.",
            )

    # Policy and overlap validation checks
    from app.domain.attendance.validators.leave_validator import LeaveValidator
    LeaveValidator.validate_leave(db, employee_id, payload.date, st, et)

    new_request = TimeOffRequest(
        employee_id=employee_id,
        date=payload.date,
        leave_type=leave_store,
        start_time=st,
        end_time=et,
        duration_hours=round(requested, 2),
        status="Pending",
    )
    db.add(new_request)

    # Keep the request and its first approval task atomic.
    try:
        db.flush()
        from app.services.approval_service import create_approval_task
        employee_obj = db.query(Employee).filter(Employee.id == employee_id).first()
        submitted_by = employee_obj.user_id if employee_obj else 1
        create_approval_task(db, request_type="timeoff", request_id=new_request.id, employee_id=employee_id, submitted_by=submitted_by)
        db.commit()
        db.refresh(new_request)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create the approval workflow") from e

    try:
        from app.services.dashboard_service import invalidate_dashboard_cache
        invalidate_dashboard_cache(db, keys=["dashboard:admin", "dashboard:hr"])
    except Exception:
        pass

    # Dispatch LeaveRequested domain event
    try:
        from app.domain.events.dispatcher import EventDispatcher
        from app.domain.events.types import LeaveRequested
        EventDispatcher.dispatch(LeaveRequested(
            employee_id=employee_id,
            leave_request_id=new_request.id,
            date=new_request.date,
            leave_type=new_request.leave_type
        ))
    except Exception as e:
        print(f"Failed to dispatch LeaveRequested event: {e}")


    approved_today = get_timeoff_duration_for_date(db, employee_id, date.today())
    approved_seconds_today = int(round(approved_today * 3600))
    refreshed_today = get_today_state(db, employee_id)
    remaining_seconds_today = int(refreshed_today["remainingSeconds"])
    remaining_today = round(remaining_seconds_today / 3600, 2)
    
    new_request.employee_name = f"{new_request.employee.first_name} {new_request.employee.last_name}"
    new_request.employee_code = new_request.employee.employee_code
    return new_request, approved_today, remaining_today, approved_seconds_today, remaining_seconds_today
