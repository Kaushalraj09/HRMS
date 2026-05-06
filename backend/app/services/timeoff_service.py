from sqlalchemy.orm import Session
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
    TOTAL_SHIFT_WORKING_HOURS,
    get_today_state,
)

SHIFT_START = time_type(9, 0)
SHIFT_END = time_type(18, 0)

def get_timeoff_by_date(db: Session, employee_id: int, target_date: date):
    return db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id,
        TimeOffRequest.date == target_date,
        TimeOffRequest.status.in_(["Approved", "Active", "Completed"])
    ).first()

def request_timeoff(db: Session, employee_id: int, request: TimeOffRequestCreate):
    if request.leave_type == "Full-Day":
        duration_hours = 8.0
    elif request.leave_type == "Half-Day":
        duration_hours = 4.0
    else:
        duration_hours = request.duration_hours

    if duration_hours < 0.5 or duration_hours > 8.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approved time should be between 30 minutes (0.5 hrs) and 8 hours."
        )

    existing = db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id,
        TimeOffRequest.date == request.date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A time-off request already exists for this date."
        )
        
    new_request = TimeOffRequest(
        employee_id=employee_id,
        date=request.date,
        leave_type=request.leave_type,
        start_time=request.start_time,
        end_time=request.end_time,
        duration_hours=duration_hours,
        status="Pending"
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

def get_my_timeoffs(db: Session, employee_id: int):
    return db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id
    ).order_by(TimeOffRequest.date.desc()).all()

def get_pending_requests(db: Session):
    return db.query(TimeOffRequest).filter(
        TimeOffRequest.status == "Pending"
    ).order_by(TimeOffRequest.created_at.desc()).all()

def approve_request(db: Session, request_id: int, action: str, admin_user_id: int, comments: str = None, approved_duration_hours: float = None):
    req = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    
    if req.status != "Pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending requests can be processed.")
        
    if action.upper() == "APPROVE":
        employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
        
        # Override duration if custom/partial approval is provided
        if approved_duration_hours is not None:
            if approved_duration_hours <= 0 or approved_duration_hours > 8:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approved duration must be > 0 and <= 8.")
            req.duration_hours = approved_duration_hours
            
        if employee.timeoff_balance_hours < req.duration_hours:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient time-off balance.")
            
        employee.timeoff_balance_hours -= req.duration_hours
        req.status = "Approved"
    elif action.upper() == "REJECT":
        req.status = "Rejected"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action. Use APPROVE or REJECT.")

    log = ApprovalLog(
        timeoff_request_id=req.id,
        action_by_user_id=admin_user_id,
        action=action.upper(),
        comments=comments
    )
    db.add(log)
    db.commit()
    db.refresh(req)
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

    lt = (payload.leave_type or "").strip().lower().replace(" ", "")
    if lt in ("fullday", "full-day"):
        leave_store = "Full-Day"
        st = SHIFT_START
        et = SHIFT_END
        requested = float(TOTAL_SHIFT_WORKING_HOURS)
    elif lt == "hourly":
        leave_store = "Hourly"
        if payload.start_time is None or payload.end_time is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time and end_time are required for Hourly time off.",
            )
        st = payload.start_time
        et = payload.end_time
        if st.minute not in (0, 30) or et.minute not in (0, 30):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time and end_time must use 30-minute intervals.",
            )
        if st < SHIFT_START or et > SHIFT_END:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time off must fall within working hours 09:00–18:00.",
            )
        if et <= st:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time must be after start_time.",
            )
        requested = _duration_hours_between(st, et, payload.date)
        if requested <= 0 or requested > TOTAL_SHIFT_WORKING_HOURS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid requested duration.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="leave_type must be 'Hourly' or 'Full Day'.",
        )

    approved_so_far = get_timeoff_duration_for_date(db, employee_id, payload.date)
    if payload.date == date.today():
        remaining_hours = today_state["remainingSeconds"] / 3600.0
    else:
        remaining_hours = max(0.0, TOTAL_SHIFT_WORKING_HOURS - approved_so_far)

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

    new_request = TimeOffRequest(
        employee_id=employee_id,
        date=payload.date,
        leave_type=leave_store,
        start_time=st,
        end_time=et,
        duration_hours=round(requested, 2),
        status="Approved",
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    approved_today = get_timeoff_duration_for_date(db, employee_id, date.today())
    approved_seconds_today = int(round(approved_today * 3600))
    refreshed_today = get_today_state(db, employee_id)
    remaining_seconds_today = int(refreshed_today["remainingSeconds"])
    remaining_today = round(remaining_seconds_today / 3600, 2)
    return new_request, approved_today, remaining_today, approved_seconds_today, remaining_seconds_today
