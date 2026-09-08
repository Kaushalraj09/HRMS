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
    role = current_user.role.name.lower() if current_user.role else ""
    if role not in ["admin", "hr"]:
        from app.models.employee import Employee
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not employee:
            return {"items": [], "page": page, "pageSize": pageSize, "totalItems": 0, "totalPages": 0}
        employeeId = employee.id

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
        decision=payload.decision,
        comment=payload.comment,
        approved_hours=payload.approved_hours,
        override=payload.override,
        override_reason=payload.override_reason,
    )
    
    return result
