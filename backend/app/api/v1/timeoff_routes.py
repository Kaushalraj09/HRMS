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
    TimeOffRequestPaginatedResponse,
    TimeOffDecisionRequest,
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
@router.post("/requests", response_model=TimeOffRequestResponse)
async def request_timeoff(
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
    
    created = timeoff_service.request_timeoff(db, employee.id, request)

    # Notify connected HR/Admin dashboards to refresh pending requests.
    await manager.broadcast(
        {
            "type": "TIMEOFF_REQUEST",
            "message": f"New time off request from employee #{employee.id}",
            "request": {
                "id": created.id,
                "employee_id": created.employee_id,
                "date": str(created.date),
                "leave_type": created.leave_type,
                "start_time": str(created.start_time) if created.start_time else None,
                "end_time": str(created.end_time) if created.end_time else None,
                "duration_hours": created.duration_hours,
                "status": created.status,
                "employee_name": created.employee_name,
                "reason": created.reason,
                "attachment_name": created.attachment_name,
            },
        }
    )

    # Dispatch notifications
    try:
        from app.services.notification_service import create_notification
        from app.models.user import User, Role
        from sqlalchemy import func

        # 1. Notify the employee
        await create_notification(
            db=db,
            user_id=current_user.id,
            type="TIMEOFF_APPLY",
            title="Time Off Request Submitted",
            message=f"You have successfully applied for time off ({created.leave_type}) on {created.date}.",
            reference_id=created.id
        )

        # 2. Notify all HR and Admin users
        try:
            from app.services.notification_service import create_notification_for_roles
            await create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="LEAVE",
                category="LEAVE_REQUEST",
                severity="WARNING",
                title="New Time Off Request",
                message=f"{employee.first_name} {employee.last_name} requested {created.leave_type} for {created.date}.",
                employee_id=employee.id,
                created_by=current_user.id,
                reference_id=created.id,
                notification_metadata={
                    "leave_type": created.leave_type,
                    "date": str(created.date),
                    "duration_hours": created.duration_hours
                }
            )
        except Exception as e:
            print(f"Failed to create admin timeoff apply notification: {e}")
    except Exception as e:
        print(f"Error dispatching apply notifications: {e}")

    return created


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

@router.get("/my-requests", response_model=TimeOffRequestPaginatedResponse)
@router.get("/requests/my", response_model=TimeOffRequestPaginatedResponse)
def get_my_timeoffs(
    page: int = 1,
    pageSize: int = 10,
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
    
    import math
    from app.models.timeoff import TimeOffRequest
    
    query = db.query(TimeOffRequest).filter(TimeOffRequest.employee_id == employee.id)
    total_items = query.count()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0
    offset = (page - 1) * pageSize
    results = query.order_by(TimeOffRequest.date.desc()).offset(offset).limit(pageSize).all()
    
    for r in results:
        r.employee_name = f"{r.employee.first_name} {r.employee.last_name}"
        r.employee_code = r.employee.employee_code
        
    return {
        "items": results,
        "page": page,
        "pageSize": pageSize,
        "totalItems": total_items,
        "totalPages": total_pages
    }

@router.get("/pending", response_model=TimeOffRequestPaginatedResponse)
def get_pending_requests(
    page: int = 1,
    pageSize: int = 10,
    search: str = "",
    leave_type: str = "",
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
    
    import math
    from app.models.timeoff import TimeOffRequest
    from app.models.employee import Employee
    
    query = db.query(TimeOffRequest).filter(TimeOffRequest.status == "Pending")
    
    if search:
        search_filter = f"%{search}%"
        query = query.join(Employee).filter(
            (Employee.first_name.ilike(search_filter)) | 
            (Employee.last_name.ilike(search_filter)) | 
            (Employee.employee_code.ilike(search_filter))
        )
        
    if leave_type:
        query = query.filter(TimeOffRequest.leave_type == leave_type)
        
    total_items = query.count()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0
    offset = (page - 1) * pageSize
    results = query.order_by(TimeOffRequest.created_at.desc()).offset(offset).limit(pageSize).all()
    
    for r in results:
        r.employee_name = f"{r.employee.first_name} {r.employee.last_name}"
        r.employee_code = r.employee.employee_code
        
    return {
        "items": results,
        "page": page,
        "pageSize": pageSize,
        "totalItems": total_items,
        "totalPages": total_pages
    }


@router.get("/requests", response_model=TimeOffRequestPaginatedResponse)
def get_all_requests(
    page: int = 1,
    pageSize: int = 10,
    search: str = "",
    leave_type: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if status.lower() == "pending" or not status:
        return get_pending_requests(page, pageSize, search, leave_type, db, current_user)
    else:
        return get_processed_requests(page, pageSize, search, leave_type, status, db, current_user)


@router.get("/history", response_model=TimeOffRequestPaginatedResponse)
def get_processed_requests(
    page: int = 1,
    pageSize: int = 10,
    search: str = "",
    leave_type: str = "",
    status: str = "",
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get processed time-off requests (Approved/Rejected) (HR/Admin only).
    """
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to view request history"
        )
    
    import math
    from app.models.timeoff import TimeOffRequest
    from app.models.employee import Employee
    
    query = db.query(TimeOffRequest).filter(TimeOffRequest.status != "Pending")
    
    if search:
        search_filter = f"%{search}%"
        query = query.join(Employee).filter(
            (Employee.first_name.ilike(search_filter)) | 
            (Employee.last_name.ilike(search_filter)) | 
            (Employee.employee_code.ilike(search_filter))
        )
        
    if leave_type:
        query = query.filter(TimeOffRequest.leave_type == leave_type)
        
    if status:
        query = query.filter(TimeOffRequest.status == status)
        
    total_items = query.count()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0
    offset = (page - 1) * pageSize
    results = query.order_by(TimeOffRequest.updated_at.desc()).offset(offset).limit(pageSize).all()
    
    for r in results:
        r.employee_name = f"{r.employee.first_name} {r.employee.last_name}"
        r.employee_code = r.employee.employee_code
        
    return {
        "items": results,
        "page": page,
        "pageSize": pageSize,
        "totalItems": total_items,
        "totalPages": total_pages
    }

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

        # Dispatch notification to database/notifications system (notify employee)
        try:
            from app.services.notification_service import create_notification
            status_label = "Approved" if action.upper() == "APPROVE" else "Rejected"
            await create_notification(
                db=db,
                user_id=employee.user_id,
                type="TIMEOFF_UPDATE",
                title=f"Time Off Request {status_label}",
                message=f"Your time off request for {result.date} has been {status_label.lower()}.",
                reference_id=result.id
            )
        except Exception as e:
            print(f"Error dispatching employee approve notifications: {e}")

        # Trigger admin notifications for HR and Admin
        try:
            from app.services.notification_service import create_notification_for_roles
            category = "LEAVE_APPROVED" if action.upper() == "APPROVE" else "LEAVE_REJECTED"
            severity = "SUCCESS" if action.upper() == "APPROVE" else "ERROR"
            status_label = "Approved" if action.upper() == "APPROVE" else "Rejected"
            await create_notification_for_roles(
                db=db,
                roles=["HR", "Admin"],
                type="LEAVE",
                category=category,
                severity=severity,
                title=f"Time Off Request {status_label}",
                message=f"Leave request {status_label.lower()} for {employee.first_name} {employee.last_name}.",
                employee_id=employee.id,
                created_by=current_user.id,
                reference_id=result.id,
                notification_metadata={
                    "leave_type": result.leave_type,
                    "date": str(result.date),
                    "action": action
                }
            )
        except Exception as e:
            print(f"Failed to create admin timeoff approve/reject notification: {e}")
    
    return result


@router.get("/bootstrap")
def get_timeoff_bootstrap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Only employees can bootstrap timeoff forms.")
    
    # Get all active leave types
    from app.models.master_data import LeaveType, Holiday
    leave_types = db.query(LeaveType).filter(LeaveType.is_active == True).all()
    holidays = db.query(Holiday).filter(Holiday.is_active == True).all()
    
    # Map leave types
    lts = []
    for lt in leave_types:
        lts.append({
            "id": lt.id,
            "name": lt.name,
            "code": lt.code,
            "unitType": lt.unit_type
        })
        
    # Balance details
    total_hours = float(employee.timeoff_balance_hours) if employee.timeoff_balance_hours is not None else 80.0
    
    # Holidays
    hols = []
    for h in holidays:
        hols.append({
            "date": str(h.holiday_date),
            "name": h.name
        })
        
    return {
        "leaveTypes": lts,
        "balance": {
            "totalHours": total_hours,
            "usedHours": 80.0 - total_hours if total_hours < 80.0 else 0.0,
            "remainingHours": total_hours
        },
        "holidays": hols
    }


@router.post("/requests/{id}/decision")
async def decide_timeoff_post(
    id: int,
    payload: TimeOffDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    action = "APPROVE" if payload.decision.lower() == "approved" else "REJECT"
    res = await approve_request(
        request_id=id,
        action=action,
        comments=payload.comment,
        approved_duration_hours=payload.approvedHours,
        db=db,
        current_user=current_user
    )
    return {
        "requestId": res.id,
        "status": res.status.lower(),
        "approvalTaskStatus": "resolved"
    }


@router.put("/requests/{request_id}/cancel")
async def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a time-off request (Employee only, or Admin/HR on behalf).
    """
    from app.models.timeoff import TimeOffRequest
    from app.models.approval_task import ApprovalTask
    from datetime import datetime
    
    req = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Time off request not found")
        
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    
    # Check authorization: must be the employee who requested it, or an admin/hr
    is_admin_or_hr = current_user.role and current_user.role.name.lower() in ["admin", "hr"]
    if not is_admin_or_hr:
        if not employee or req.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
            
    if req.status.lower() in ["cancelled", "rejected"]:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status.lower()}")

    # If it was approved, refund the timeoff hours
    if req.status.lower() == "approved":
        req_employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
        if req_employee:
            current_balance = req_employee.timeoff_balance_hours if req_employee.timeoff_balance_hours is not None else 80.0
            req_employee.timeoff_balance_hours = current_balance + req.duration_hours

    req.status = "Cancelled"
    
    # Update any matching ApprovalTask to cancelled
    task = db.query(ApprovalTask).filter(
        ApprovalTask.request_type == "timeoff",
        ApprovalTask.request_id == req.id,
        ApprovalTask.status == "pending"
    ).first()
    if task:
        task.status = "cancelled"
        task.reviewed_by = current_user.id
        task.reviewed_at = datetime.now()
        task.decision_comment = "Cancelled by employee"

    db.commit()
    db.refresh(req)
    
    # Dispatch LeaveCancelled domain event
    try:
        from app.domain.events.dispatcher import EventDispatcher
        from app.domain.events.types import LeaveCancelled
        EventDispatcher.dispatch(LeaveCancelled(
            employee_id=req.employee_id,
            leave_request_id=req.id,
            date=req.date
        ))
    except Exception as e:
        print(f"Failed to dispatch LeaveCancelled event: {e}")
        
    # Notify employee (if admin cancelled it)
    try:
        from app.services.notification_service import create_notification
        await create_notification(
            db=db,
            user_id=req.employee.user_id,
            type="TIMEOFF_UPDATE",
            title="Time Off Request Cancelled",
            message=f"Your time off request for {req.date} has been cancelled.",
            reference_id=req.id
        )
    except Exception as e:
        print(f"Failed to create cancellation notification for employee: {e}")
        
    # Trigger admin notifications for HR and Admin
    try:
        from app.services.notification_service import create_notification_for_roles
        req_emp = req.employee
        await create_notification_for_roles(
            db=db,
            roles=["HR", "Admin"],
            type="LEAVE",
            category="LEAVE_CANCELLED",
            severity="INFO",
            title="Time Off Request Cancelled",
            message=f"{req_emp.first_name} {req_emp.last_name} cancelled their leave request.",
            employee_id=req_emp.id,
            created_by=current_user.id,
            reference_id=req.id,
            notification_metadata={
                "leave_type": req.leave_type,
                "date": str(req.date)
            }
        )
    except Exception as e:
        print(f"Failed to create admin leave cancelled notification: {e}")
        
    return {
        "success": True,
        "message": "Time-off request cancelled successfully",
        "requestId": req.id,
        "status": req.status
    }


