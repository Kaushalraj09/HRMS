from sqlalchemy.orm import Session
from app.models.approval_task import ApprovalTask
from app.models.employee import Employee
from app.models.user import User
from app.services import timeoff_service
from app.models.attendance import AttendanceRegularizationRequest
from app.models.timeoff import TimeOffRequest
from fastapi import HTTPException
from datetime import datetime

def create_approval_task(db: Session, request_type: str, request_id: int, employee_id: int, submitted_by: int) -> ApprovalTask:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    task = ApprovalTask(
        request_type=request_type,
        request_id=request_id,
        employee_id=employee_id,
        status="pending",
        submitted_by=submitted_by,
        assigned_role="manager" if employee and employee.reporting_manager_id else "hr"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def _role_name(user: User) -> str:
    return user.role.name.lower() if user and user.role else ""


def _is_assigned_manager(task: ApprovalTask, user: User) -> bool:
    return bool(
        task.employee
        and task.employee.reporting_manager
        and task.employee.reporting_manager.user_id == user.id
    )


def get_pending_tasks(db: Session, current_user: User) -> dict:
    query = db.query(ApprovalTask).filter(ApprovalTask.status == "pending")
    role = _role_name(current_user)
    if role in {"admin", "hr"}:
        query = query.filter(ApprovalTask.assigned_role == "hr")
    else:
        manager_employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not manager_employee:
            tasks = []
        else:
            query = (
                query
                .join(Employee, ApprovalTask.employee_id == Employee.id)
                .filter(
                    ApprovalTask.assigned_role == "manager",
                    Employee.reporting_manager_id == manager_employee.id,
                )
            )
            tasks = query.order_by(ApprovalTask.created_at.desc()).all()
    if role in {"admin", "hr"}:
        tasks = query.order_by(ApprovalTask.created_at.desc()).all()
    
    items = []
    for t in tasks:
        emp_name = f"{t.employee.first_name} {t.employee.last_name}" if t.employee else f"Employee #{t.employee_id}"
        items.append({
            "id": t.id,
            "requestType": t.request_type,
            "requestId": t.request_id,
            "employeeId": t.employee_id,
            "employeeName": emp_name,
            "status": t.status,
            "submittedAt": t.created_at,
            "priority": t.priority,
            "assignedRole": t.assigned_role,
        })
        
    # Count totals
    timeoff_count = len([task for task in tasks if task.request_type == "timeoff"])
    reg_count = len([task for task in tasks if task.request_type == "regularization"])
    
    return {
        "items": items,
        "counts": {
            "timeoff": timeoff_count,
            "regularization": reg_count,
            "total": timeoff_count + reg_count
        }
    }

def get_history_tasks(db: Session, page: int = 1, limit: int = 10, request_type: str = None, employee_id: int = None) -> dict:
    import math
    query = db.query(ApprovalTask).filter(ApprovalTask.status != "pending")
    if request_type:
        query = query.filter(ApprovalTask.request_type == request_type)
    if employee_id:
        query = query.filter(ApprovalTask.employee_id == employee_id)
        
    total_items = query.count()
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 0
    offset = (page - 1) * limit
    results = query.order_by(ApprovalTask.updated_at.desc()).offset(offset).limit(limit).all()
    
    items = []
    for t in results:
        emp_name = f"{t.employee.first_name} {t.employee.last_name}" if t.employee else f"Employee #{t.employee_id}"
        items.append({
            "id": t.id,
            "requestType": t.request_type,
            "requestId": t.request_id,
            "employeeId": t.employee_id,
            "employeeName": emp_name,
            "status": t.status,
            "submittedAt": t.created_at,
            "priority": t.priority,
            "assignedRole": t.assigned_role,
        })
        
    return {
        "items": items,
        "page": page,
        "pageSize": limit,
        "totalItems": total_items,
        "totalPages": total_pages
    }

def decide_task(db: Session, task_id: int, reviewer_id: int, decision: str, comment: str = None, approved_hours: float = None) -> ApprovalTask:
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Approval task not found")
        
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Approval task has already been processed")

    reviewer = db.query(User).filter(User.id == reviewer_id).first()
    reviewer_role = _role_name(reviewer)
    if task.assigned_role == "manager":
        if reviewer_role not in {"admin", "hr"} and not _is_assigned_manager(task, reviewer):
            raise HTTPException(status_code=403, detail="Only the assigned reporting manager can review this request")
        task.reviewed_by = reviewer_id
        task.reviewed_at = datetime.now()
        task.decision_comment = comment
        if decision == "approved":
            task.assigned_role = "hr"
            if task.request_type == "timeoff":
                req = db.query(TimeOffRequest).filter(TimeOffRequest.id == task.request_id).first()
                if req:
                    req.approval_stage = "HR"
            elif task.request_type == "regularization":
                reg_req = db.query(AttendanceRegularizationRequest).filter(AttendanceRegularizationRequest.id == task.request_id).first()
                if reg_req:
                    reg_req.manager_decision = "approved"
                    reg_req.status = "pending_hr"
            db.commit()
            db.refresh(task)
            return task
        # Manager rejection is final.
    elif task.assigned_role == "hr" and reviewer_role not in {"admin", "hr"}:
        raise HTTPException(status_code=403, detail="HR/Admin approval is required for this stage")

    task.status = decision
    task.reviewed_by = reviewer_id
    task.reviewed_at = datetime.now()
    task.decision_comment = comment
    
    # Propagate to sub-modules
    if task.request_type == "timeoff":
        action = "APPROVE" if decision == "approved" else "REJECT"
        timeoff_service.approve_request(db, task.request_id, action, reviewer_id, comment, approved_hours)
    elif task.request_type == "regularization":
        # Process regularization request
        from app.models.attendance import AttendanceRegularizationRequest
        reg_req = db.query(AttendanceRegularizationRequest).filter(AttendanceRegularizationRequest.id == task.request_id).first()
        if reg_req:
            reg_req.status = decision
            reg_req.reviewed_by = reviewer_id
            reg_req.reviewed_at = datetime.now()
            reg_req.review_comment = comment
            
            if decision == "approved":
                # Apply regularization to attendance record
                from app.models.attendance import Attendance
                from app.services.attendance_service import calculate_attendance_metrics
                attendance = db.query(Attendance).filter(
                    Attendance.employee_id == reg_req.employee_id,
                    Attendance.date == reg_req.attendance_date
                ).first()
                if attendance:
                    if reg_req.requested_punch_in:
                        attendance.punch_in = reg_req.requested_punch_in
                    if reg_req.requested_punch_out:
                        attendance.punch_out = reg_req.requested_punch_out
                    attendance.status = "Present"
                    attendance.requires_regularization = False
                    calculate_attendance_metrics(attendance)
                    db.commit()
            
    db.commit()
    db.refresh(task)
    return task
