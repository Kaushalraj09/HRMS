from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.approval import ApprovalQueueResponse, ApprovalDecisionRequest, ApprovalTaskResponse
from app.services import approval_service

router = APIRouter(prefix="/approvals", tags=["Approval Center"])

def check_approval_access(user: User):
    if not user.role or user.role.name.lower() not in ["admin", "hr", "employee"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

@router.get("/pending", response_model=ApprovalQueueResponse)
def get_pending(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_approval_access(current_user)
    return approval_service.get_pending_tasks(db, current_user)

@router.get("/history")
def get_history(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    requestType: str = Query(None),
    employeeId: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_approval_access(current_user)
    return approval_service.get_history_tasks(
        db, page=page, limit=pageSize, request_type=requestType, employee_id=employeeId
    )

@router.post("/{approvalTaskId}/decision", response_model=ApprovalTaskResponse)
async def decide_approval(
    approvalTaskId: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_approval_access(current_user)
    
    from app.models.approval_task import ApprovalTask
    task = db.query(ApprovalTask).filter(ApprovalTask.id == approvalTaskId).first()
    task_type = task.request_type if task else None
    task_req_id = task.request_id if task else None
    
    result = approval_service.decide_task(
        db, task_id=approvalTaskId, reviewer_id=current_user.id,
        decision=payload.decision, comment=payload.comment, approved_hours=payload.approved_hours
    )
    
    # If it is a timeoff request, trigger real-time notifications
    if task_type == "timeoff" and task_req_id:
        from app.models.timeoff import TimeOffRequest
        from app.models.employee import Employee
        timeoff_req = db.query(TimeOffRequest).filter(TimeOffRequest.id == task_req_id).first()
        if timeoff_req:
            employee = db.query(Employee).filter(Employee.id == timeoff_req.employee_id).first()
            if employee:
                status_label = "Approved" if payload.decision.lower() == "approved" else "Rejected"
                
                # Notify the employee
                try:
                    from app.services.notification_service import create_notification
                    await create_notification(
                        db=db,
                        user_id=employee.user_id,
                        type="TIMEOFF_UPDATE",
                        title=f"Time Off Request {status_label}",
                        message=f"Your time off request for {timeoff_req.date} has been {status_label.lower()}.",
                        reference_id=timeoff_req.id
                    )
                except Exception as e:
                    print(f"Error dispatching employee approve notifications from approval task: {e}")
                
                # Notify all HR and Admin users
                try:
                    from app.services.notification_service import create_notification_for_roles
                    category = "LEAVE_APPROVED" if payload.decision.lower() == "approved" else "LEAVE_REJECTED"
                    severity = "SUCCESS" if payload.decision.lower() == "approved" else "ERROR"
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
                        reference_id=timeoff_req.id,
                        notification_metadata={
                            "leave_type": timeoff_req.leave_type,
                            "date": str(timeoff_req.date),
                            "action": payload.decision
                        }
                    )
                except Exception as e:
                    print(f"Failed to create admin timeoff approve/reject notification from approval task: {e}")
                    
    return result
