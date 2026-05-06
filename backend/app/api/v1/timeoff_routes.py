from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.schemas.timeoff import (
    TimeOffRequestCreate,
    TimeOffRequestResponse,
    TimeOffApplyPayload,
    TimeOffApplyResponse,
)
from app.services import timeoff_service, attendance_service
from app.core.websocket_manager import manager

router = APIRouter(prefix="/timeoff", tags=["timeoff"])

@router.get("/remaining/{employee_id}")
def get_remaining_hours(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the dynamically calculated remaining working hours for today.
    """
    # Assuming role check is either admin/hr or the employee themselves
    if current_user.role.name not in ["Admin", "HR"]:
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not employee or employee.id != employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
            
    today_state = attendance_service.get_today_state(db, employee_id)
    return {"remaining_hours": today_state["remainingHours"]}

@router.post("/request", response_model=TimeOffRequestResponse)
def request_timeoff(
    request: TimeOffRequestCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Request time-off for the current employee.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only employees can request time-off"
        )
    
    return timeoff_service.request_timeoff(db, employee.id, request)


@router.post("/apply", response_model=TimeOffApplyResponse)
def apply_time_off_inline(
    payload: TimeOffApplyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit time off from inline form: validates shift, interval, quota; stores as Approved.
    Returns today’s approved/remaining totals after commit.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can request time off.",
        )

    row, approved_today, remaining_today, approved_seconds_today, remaining_seconds_today = timeoff_service.apply_time_off(db, employee.id, payload)
    return TimeOffApplyResponse(
        id=row.id,
        employee_id=row.employee_id,
        date=row.date,
        leave_type=row.leave_type,
        start_time=row.start_time,
        end_time=row.end_time,
        duration_hours=row.duration_hours,
        status=row.status,
        approved_hours_today=approved_today,
        remaining_hours_today=remaining_today,
        approved_seconds_today=approved_seconds_today,
        remaining_seconds_today=remaining_seconds_today,
    )


@router.get("/by-date", response_model=TimeOffRequestResponse)
def get_timeoff_by_date(
    target_date: date,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get approved time-off for a specific date.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only employees can view their time-off"
        )
    
    timeoff = timeoff_service.get_timeoff_by_date(db, employee.id, target_date)
    if not timeoff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No approved time-off found for this date"
        )
    return timeoff

@router.get("/my-requests", response_model=List[TimeOffRequestResponse])
def get_my_timeoffs(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get all time-off requests for the current employee.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only employees can view their time-off"
        )
    return timeoff_service.get_my_timeoffs(db, employee.id)

@router.get("/pending", response_model=List[TimeOffRequestResponse])
def get_pending_requests(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get all pending time-off requests (HR/Admin only).
    """
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to view pending requests"
        )
    return timeoff_service.get_pending_requests(db)

@router.put("/approve/{request_id}", response_model=TimeOffRequestResponse)
async def approve_request(
    request_id: int,
    action: str, # "APPROVE" or "REJECT"
    comments: str = None,
    approved_duration_hours: float = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve or reject a time-off request (HR/Admin only).
    """
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to process requests"
        )
    
    result = timeoff_service.approve_request(db, request_id, action, current_user.id, comments, approved_duration_hours)
    
    # Broadcast to the employee who made the request
    employee = db.query(Employee).filter(Employee.id == result.employee_id).first()
    if employee:
        await manager.send_personal_message(
            {
                "type": "TIMEOFF_UPDATE", 
                "status": result.status, 
                "duration": result.duration_hours,
                "message": f"Your time-off request for {result.date} has been {result.status.lower()}."
            },
            employee.user_id
        )
    
    return result
