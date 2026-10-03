from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.schemas.employee import EmployeeListResponse, EmployeeResponse
from app.schemas.attendance import ManagerAttendancePaginatedResponse
from app.schemas.timeoff import TimeOffRequestPaginatedResponse, TimeOffRequestResponse
from app.services import manager_service

router = APIRouter(prefix="/manager", tags=["manager-portal"])


def get_current_manager(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> tuple[User, Employee]:
    """Ensure the user has Manager or Admin role and resolve their linked employee record."""
    role = (current_user.role.name if current_user.role else "").lower()
    if role not in ["manager", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: Manager role required."
        )

    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp and role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No employee profile associated with this manager account."
        )

    return current_user, emp


class ManagerDecisionPayload(BaseModel):
    comment: Optional[str] = None


class ManagerRejectPayload(BaseModel):
    comment: str


@router.get("/dashboard-stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    is_admin = (current_user.role.name if current_user.role else "").lower() == "admin"
    if not manager_emp and not is_admin:
        return {
            "totalEmployees": 0, "presentToday": 0, "absentToday": 0,
            "onLeaveToday": 0, "lateToday": 0, "currentlyWorking": 0, "pendingApprovals": 0
        }
    return manager_service.get_manager_dashboard_stats(db, manager_emp, is_admin=is_admin)


@router.get("/attendance-trend")
def get_attendance_trend(
    period: str = Query("This Month"),
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    is_admin = (current_user.role.name if current_user.role else "").lower() == "admin"
    return manager_service.get_manager_attendance_trend(
        db, manager_emp, period=period, is_admin=is_admin
    )


@router.get("/team", response_model=EmployeeListResponse)
def get_team_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str = "",
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    is_admin = (current_user.role.name if current_user.role else "").lower() == "admin"
    if not manager_emp and not is_admin:
        return {"data": [], "total": 0}
    return manager_service.get_manager_team_employees(db, manager_emp, page=page, limit=limit, search=search, is_admin=is_admin)


@router.get("/team/{employee_id}", response_model=EmployeeResponse)
def get_team_employee_detail(
    employee_id: int,
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    role = (current_user.role.name if current_user.role else "").lower()
    if role != "admin" and (not manager_emp or employee.reporting_manager_id != manager_emp.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view details of an employee not assigned to your team."
        )
    return employee


@router.get("/attendance", response_model=ManagerAttendancePaginatedResponse)
def get_team_attendance(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    fromDate: Optional[str] = None,
    toDate: Optional[str] = None,
    employeeId: Optional[int] = None,
    status: str = "",
    search: str = "",
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    is_admin = (current_user.role.name if current_user.role else "").lower() == "admin"
    if not manager_emp and not is_admin:
        return {"items": [], "total": 0, "page": page, "limit": limit, "totalPages": 0}

    parsed_from = date.fromisoformat(fromDate) if fromDate and fromDate.strip() else None
    parsed_to = date.fromisoformat(toDate) if toDate and toDate.strip() else None

    # If employeeId provided, ensure it belongs to this manager
    if employeeId and not is_admin:
        target_emp = db.query(Employee).filter(Employee.id == employeeId).first()
        if not target_emp or target_emp.reporting_manager_id != (manager_emp.id if manager_emp else -1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view attendance for employees outside your assigned team."
            )

    return manager_service.get_manager_team_attendance(
        db, manager_emp,
        page=page, limit=limit,
        from_date=parsed_from, to_date=parsed_to,
        employee_id=employeeId, status_filter=status, search=search,
        is_admin=is_admin
    )


@router.get("/leave-requests", response_model=TimeOffRequestPaginatedResponse)
def get_team_leave_requests(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    status: str = "",
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    is_admin = (current_user.role.name if current_user.role else "").lower() == "admin"
    if not manager_emp and not is_admin:
        return {"items": [], "page": page, "pageSize": pageSize, "totalItems": 0, "totalPages": 0}

    return manager_service.get_manager_leave_requests(
        db, manager_emp, status_filter=status, page=page, limit=pageSize, is_admin=is_admin
    )


@router.get("/leave-requests/{request_id}", response_model=TimeOffRequestResponse)
def get_leave_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    from app.models.timeoff import TimeOffRequest
    current_user, manager_emp = mgr_tuple
    req = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    role = (current_user.role.name if current_user.role else "").lower()
    if role != "admin" and (not manager_emp or not req.employee or req.employee.reporting_manager_id != manager_emp.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Leave request does not belong to an employee in your team."
        )

    return manager_service.enrich_timeoff_with_manager_info(db, req)


@router.post("/leave-requests/{request_id}/approve", response_model=TimeOffRequestResponse)
def approve_team_leave(
    request_id: int,
    payload: ManagerDecisionPayload,
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    if not manager_emp:
        raise HTTPException(status_code=400, detail="Manager employee profile required")

    result = manager_service.decide_leave_request(
        db=db,
        manager_user=current_user,
        manager_employee=manager_emp,
        request_id=request_id,
        decision="approved",
        comment=payload.comment
    )
    return result["request"]


@router.post("/leave-requests/{request_id}/reject", response_model=TimeOffRequestResponse)
def reject_team_leave(
    request_id: int,
    payload: ManagerRejectPayload,
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    if not manager_emp:
        raise HTTPException(status_code=400, detail="Manager employee profile required")

    if not payload.comment or not payload.comment.strip():
        raise HTTPException(status_code=400, detail="Remarks are required when rejecting a leave request.")

    result = manager_service.decide_leave_request(
        db=db,
        manager_user=current_user,
        manager_employee=manager_emp,
        request_id=request_id,
        decision="rejected",
        comment=payload.comment.strip()
    )
    return result["request"]


@router.post("/send-attendance-reminder")
async def send_team_attendance_reminder(
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    is_admin = (current_user.role.name if current_user.role else "").lower() == "admin"
    return await manager_service.send_team_attendance_reminders(
        db, manager_user=current_user, manager_employee=manager_emp, is_admin=is_admin
    )


@router.get("/team-performance")
def get_team_performance(
    db: Session = Depends(get_db),
    mgr_tuple: tuple[User, Employee] = Depends(get_current_manager)
):
    current_user, manager_emp = mgr_tuple
    is_admin = (current_user.role.name if current_user.role else "").lower() == "admin"
    return manager_service.get_manager_team_performance(
        db, manager_employee=manager_emp, is_admin=is_admin
    )


