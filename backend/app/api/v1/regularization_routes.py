from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.core.database import get_db
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.attendance import Attendance, AttendanceRegularizationRequest
from app.schemas.regularization import (
    RegularizationRequestCreate,
    RegularizationRequestDecision,
    RegularizationRequestResponse,
    RegularizationRequestPaginatedResponse,
)
from app.api.deps import get_current_user
from app.services.attendance_service import to_attendance_response, log_audit_trail_sync
from app.core.websocket_manager import manager

router = APIRouter(prefix="/regularizations", tags=["Attendance Regularization"])

@router.post("", response_model=RegularizationRequestResponse)
async def submit_regularization(
    request: RegularizationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find employee
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can submit regularization requests"
        )

    # Check if request already exists for this date
    existing = db.query(AttendanceRegularizationRequest).filter(
        AttendanceRegularizationRequest.employee_id == employee.id,
        AttendanceRegularizationRequest.attendance_date == request.attendance_date
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A regularization request for this date already exists"
        )

    # Check if attendance record exists
    attendance = db.query(Attendance).filter(
        Attendance.employee_id == employee.id,
        Attendance.date == request.attendance_date
    ).first()
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No attendance record found for this date to regularize"
        )

    new_request = AttendanceRegularizationRequest(
        employee_id=employee.id,
        attendance_date=request.attendance_date,
        requested_punch_in=request.requested_punch_in,
        requested_punch_out=request.requested_punch_out,
        reason_type=request.reason_type,
        reason_text=request.reason_text,
        status="pending"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Create unified ApprovalTask
    try:
        from app.services.approval_service import create_approval_task
        create_approval_task(db, request_type="regularization", request_id=new_request.id, employee_id=employee.id, submitted_by=current_user.id)
    except Exception as e:
        print(f"Failed to create regularization approval task: {e}")

    log_audit_trail_sync(db, "REGULARIZATION_SUBMIT", employee.id, f"Submitted regularization request for {request.attendance_date}")

    # Broadcast websocket alert to HR/Admin users of type REGULARIZATION_REQUEST
    await manager.broadcast(
        {
            "type": "REGULARIZATION_REQUEST",
            "message": f"New regularization request from {employee.first_name} {employee.last_name}",
            "request_id": new_request.id,
            "employee_id": employee.id
        }
    )

    try:
        from app.services.notification_service import create_notification
        from app.models.user import User, Role
        from sqlalchemy import func

        # 1. Notify the employee
        await create_notification(
            db=db,
            user_id=current_user.id,
            type="ATTENDANCE",
            title="Regularization Request Submitted",
            message=f"You have successfully applied for attendance regularization on {new_request.attendance_date}.",
            reference_id=new_request.id
        )

        # 2. Notify all HR users
        hr_users = db.query(User).join(Role).filter(func.lower(Role.name) == "hr").all()
        for hr_user in hr_users:
            await create_notification(
                db=db,
                user_id=hr_user.id,
                type="ATTENDANCE",
                title="New Regularization Request",
                message=f"Employee {employee.first_name} {employee.last_name} (ID: {employee.id}) has submitted an attendance regularization request for {new_request.attendance_date}.",
                reference_id=new_request.id
            )
    except Exception as e:
        print(f"Error dispatching regularization apply notifications: {e}")

    # Return response mapped
    return _map_request_to_response(new_request)

@router.get("/my", response_model=RegularizationRequestPaginatedResponse)
async def get_my_regularizations(
    page: int = 1,
    pageSize: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can view their requests"
        )

    import math
    query = db.query(AttendanceRegularizationRequest).filter(
        AttendanceRegularizationRequest.employee_id == employee.id
    )

    total_items = query.count()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0
    offset = (page - 1) * pageSize
    requests = query.order_by(AttendanceRegularizationRequest.created_at.desc()).offset(offset).limit(pageSize).all()

    return {
        "items": [_map_request_to_response(r) for r in requests],
        "page": page,
        "pageSize": pageSize,
        "totalItems": total_items,
        "totalPages": total_pages
    }

@router.get("", response_model=RegularizationRequestPaginatedResponse)
async def get_all_regularizations(
    page: int = 1,
    pageSize: int = 10,
    search: str = "",
    reason_type: str = "",
    status: str = "pending",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Admin or HR roles
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only Admin or HR can view regularization requests."
        )

    import math
    query = db.query(AttendanceRegularizationRequest)
    if status:
        query = query.filter(AttendanceRegularizationRequest.status == status.lower())
        
    if search:
        search_filter = f"%{search}%"
        query = query.join(Employee).filter(
            (Employee.first_name.ilike(search_filter)) | 
            (Employee.last_name.ilike(search_filter)) | 
            (Employee.employee_code.ilike(search_filter))
        )
        
    if reason_type:
        query = query.filter(AttendanceRegularizationRequest.reason_type == reason_type)

    total_items = query.count()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0
    offset = (page - 1) * pageSize
    requests = query.order_by(AttendanceRegularizationRequest.created_at.desc()).offset(offset).limit(pageSize).all()

    return {
        "items": [_map_request_to_response(r) for r in requests],
        "page": page,
        "pageSize": pageSize,
        "totalItems": total_items,
        "totalPages": total_pages
    }


@router.get("/pending", response_model=RegularizationRequestPaginatedResponse)
async def get_pending_regularizations(
    page: int = 1,
    pageSize: int = 10,
    search: str = "",
    reason_type: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Admin or HR roles
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin or HR can view pending regularization requests."
        )

    import math
    query = db.query(AttendanceRegularizationRequest).filter(
        AttendanceRegularizationRequest.status == "pending"
    )

    if search:
        search_filter = f"%{search}%"
        query = query.join(Employee).filter(
            (Employee.first_name.ilike(search_filter)) | 
            (Employee.last_name.ilike(search_filter)) | 
            (Employee.employee_code.ilike(search_filter))
        )
        
    if reason_type:
        query = query.filter(AttendanceRegularizationRequest.reason_type == reason_type)

    total_items = query.count()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0
    offset = (page - 1) * pageSize
    requests = query.order_by(AttendanceRegularizationRequest.created_at.asc()).offset(offset).limit(pageSize).all()

    return {
        "items": [_map_request_to_response(r) for r in requests],
        "page": page,
        "pageSize": pageSize,
        "totalItems": total_items,
        "totalPages": total_pages
    }

@router.put("/{request_id}/decision", response_model=RegularizationRequestResponse)
@router.post("/{request_id}/decision", response_model=RegularizationRequestResponse)
async def review_regularization(
    request_id: int,
    decision: RegularizationRequestDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Admin or HR roles
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin or HR can review regularization requests."
        )

    req = db.query(AttendanceRegularizationRequest).filter(
        AttendanceRegularizationRequest.id == request_id
    ).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regularization request not found"
        )

    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request is already reviewed"
        )

    req.status = decision.status
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.now()
    req.review_comment = decision.review_comment

    # Update matching ApprovalTask status if pending
    try:
        from app.models.approval_task import ApprovalTask
        task = db.query(ApprovalTask).filter(
            ApprovalTask.request_type == "regularization",
            ApprovalTask.request_id == req.id,
            ApprovalTask.status == "pending"
        ).first()
        if task:
            task.status = decision.status
            task.reviewed_by = current_user.id
            task.reviewed_at = datetime.now()
            task.decision_comment = decision.review_comment
    except Exception as e:
        print(f"Failed to synchronize regularization approval task: {e}")


    if decision.status == "approved":
        # Find attendance record and update it
        attendance = db.query(Attendance).filter(
            Attendance.employee_id == req.employee_id,
            Attendance.date == req.attendance_date
        ).first()
        
        if attendance:
            # Update punch times
            if req.requested_punch_in:
                attendance.punch_in = req.requested_punch_in
            if req.requested_punch_out:
                attendance.punch_out = req.requested_punch_out
            
            # Reset flags, checkout source, and requires_regularization
            attendance.checkout_source = "MANUAL"
            attendance.requires_regularization = False
            
            # Recompute attendance working hours & status & flags
            from app.services.time_calculator import calculate_times
            calculate_times(attendance)
            
            # Ensure "REGULARIZED" flag is added
            current_flags = attendance.flags
            if "REGULARIZED" not in current_flags:
                current_flags.append("REGULARIZED")
            # Remove MISSED_PUNCH and AUTO_CHECKOUT if present
            if "MISSED_PUNCH" in current_flags:
                current_flags.remove("MISSED_PUNCH")
            if "AUTO_CHECKOUT" in current_flags:
                current_flags.remove("AUTO_CHECKOUT")
            attendance.flags = current_flags

            db.add(attendance)
            
            # Trigger notification to the employee
            from app.services.notification_service import create_notification
            try:
                # Get employee user ID
                emp = db.query(Employee).filter(Employee.id == req.employee_id).first()
                if emp:
                    await create_notification(
                        db=db,
                        user_id=emp.user_id,
                        type="ATTENDANCE",
                        title="Regularization Approved",
                        message=f"Your attendance regularization request for {req.attendance_date} has been APPROVED.",
                        reference_id=attendance.id
                    )
                    await manager.send_personal_message(
                        {
                            "type": "REGULARIZATION_UPDATE",
                            "status": "Approved",
                            "message": f"Your regularization request for {req.attendance_date} has been APPROVED."
                        },
                        emp.user_id
                    )
            except Exception as e:
                print(f"Failed to create regularization approved notification: {e}")

    elif decision.status == "rejected":
        # Just notify the employee
        from app.services.notification_service import create_notification
        try:
            emp = db.query(Employee).filter(Employee.id == req.employee_id).first()
            if emp:
                await create_notification(
                    db=db,
                    user_id=emp.user_id,
                    type="ATTENDANCE",
                    title="Regularization Rejected",
                    message=f"Your attendance regularization request for {req.attendance_date} has been REJECTED. Reason: {decision.review_comment or 'N/A'}"
                )
                await manager.send_personal_message(
                    {
                        "type": "REGULARIZATION_UPDATE",
                        "status": "Rejected",
                        "message": f"Your regularization request for {req.attendance_date} has been REJECTED."
                    },
                    emp.user_id
                )
        except Exception as e:
            print(f"Failed to create regularization rejected notification: {e}")

    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit_trail_sync(db, f"REGULARIZATION_{decision.status.upper()}", req.employee_id, f"Regularization request {request_id} reviewed and {decision.status}")

    return _map_request_to_response(req)

def _map_request_to_response(r: AttendanceRegularizationRequest) -> RegularizationRequestResponse:
    # Resolve reviewer name
    reviewer_name = None
    if r.reviewer:
        # Check if reviewer has an employee profile, else user profile
        emp = r.reviewer.employee_profile[0] if getattr(r.reviewer, "employee_profile", None) else None
        reviewer_name = emp.first_name + " " + emp.last_name if emp else r.reviewer.email

    # Resolve employee name/code
    emp_name = None
    emp_code = None
    if r.employee:
        emp_name = f"{r.employee.first_name} {r.employee.last_name}"
        emp_code = r.employee.employee_code

    return RegularizationRequestResponse(
        id=r.id,
        employee_id=r.employee_id,
        employee_name=emp_name,
        employee_code=emp_code,
        attendance_date=r.attendance_date,
        requested_punch_in=r.requested_punch_in,
        requested_punch_out=r.requested_punch_out,
        reason_type=r.reason_type,
        reason_text=r.reason_text,
        status=r.status,
        reviewed_by=r.reviewed_by,
        reviewed_by_name=reviewer_name,
        reviewed_at=r.reviewed_at,
        review_comment=r.review_comment,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )
