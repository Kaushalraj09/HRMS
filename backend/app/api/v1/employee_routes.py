from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.core.enums import UserRole
from app.schemas.employee import (
    AssignTeamRequest,
    ChangeEmployeeCodeRequest,
    MigrateToAivanCodeRequest,
    EmployeeCodeHistoryResponse,
    EmployeeCreate,
    EmployeeCredentialsResponse,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services import employee_service, employee_code_service
from app.services.account_access_service import InvitationDeliveryError

router = APIRouter(prefix="/employees", tags=["employee-management"])

@router.post("", response_model=EmployeeResponse)
def add_employee(
    request: EmployeeCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to add employees"
        )
    if not request.work_location or not request.work_location.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work location is required."
        )
    target_role = (request.role or "employee").lower().strip()
    is_top_level_role = target_role in ["manager", "hr", "admin"]
    if not is_top_level_role:
        if not request.reporting_manager_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigning a reporting manager is mandatory."
            )
    if request.reporting_manager_id:
        manager = db.query(Employee).filter(Employee.id == request.reporting_manager_id, Employee.status != "Deleted").first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected reporting manager does not exist or has been deleted."
            )
    try:
        return employee_service.create_employee(db, request)
    except InvitationDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("", response_model=EmployeeListResponse)
def get_all_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000),
    search: str = "",
    department: str = "",
    type: str = "",
    status: str = "",
    exclude_hr: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to view all employees"
        )
    return employee_service.list_employees(
        db,
        page=page,
        limit=limit,
        search=search,
        department=department,
        employee_type=type,
        status=status,
        exclude_hr=exclude_hr,
    )


@router.get("/next-code")
def get_next_employee_code_preview(
    prefix: str = "AIVAN",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns preview of next sequential employee code."""
    seq = employee_code_service.get_or_create_sequence(db, prefix)
    from app.utils.employee_code import format_employee_code
    formatted = format_employee_code(seq.next_number, prefix=seq.prefix, padding=seq.padding)
    return {
        "prefix": seq.prefix,
        "nextNumber": seq.next_number,
        "nextCode": formatted,
    }


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    role = current_user.role.name.lower() if current_user.role else ""
    if role not in [UserRole.ADMIN, UserRole.HR]:
        # For non-admin/hr users, they can only view their own employee record
        employee = employee_service.get_employee_by_id(db, employee_id)
        if not employee or employee.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view other employee details"
            )
        return employee

    employee = employee_service.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

def generate_random_password(length: int = 12) -> str:
    import secrets
    import string
    # Exclude characters that could cause JSON escaping or visual ambiguity
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

@router.get("/{employee_id}/credentials", response_model=EmployeeCredentialsResponse)
def get_user_credentials(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to view user credentials"
        )

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    return {
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "username": user.email,
        "email": user.email,
        "activation_required": True,
        "temporary_password_hint": "Temporary testing password: first 5 email letters + @1234. Replace with setup email after SMTP is configured.",
        "status": user.status
    }

@router.post("/{employee_id}/reset-access", response_model=EmployeeCredentialsResponse)
def reset_user_access(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to reset user access"
        )

    # Trigger password reset by email or the temporary mock delivery used while
    # SMTP is unavailable in the current deployment.
    from app.services.auth_service import generate_reset_token
    from app.services.mail_service import send_reset_email
    from app.core.config import settings
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password?token={generate_reset_token(user)}"
    send_reset_email(user.email, user.display_name, reset_link)

    return {
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "username": user.email,
        "email": user.email,
        "activation_required": True,
        "temporary_password_hint": "Temporary testing password: first 5 email letters + @1234. Replace with setup email after SMTP is configured.",
        "status": user.status
    }


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int, 
    request: EmployeeUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to update employees"
        )

    if request.work_location is not None and not request.work_location.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work location cannot be empty."
        )

    existing_employee = employee_service.get_employee_by_id(db, employee_id)
    if not existing_employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = request.model_dump(exclude_unset=True)
    if "reporting_manager_id" in update_data:
        new_mgr_id = update_data["reporting_manager_id"]
        if new_mgr_id is not None:
            if new_mgr_id == employee_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An employee cannot be their own reporting manager."
                )
            manager = db.query(Employee).filter(
                Employee.id == new_mgr_id,
                Employee.status != "Deleted"
            ).first()
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected reporting manager does not exist or has been deleted."
                )
        else:
            role_to_check = update_data.get("role")
            if not role_to_check:
                target_user = db.query(User).filter(User.id == existing_employee.user_id).first()
                if target_user and target_user.role:
                    role_to_check = target_user.role.name
            if (role_to_check or "employee").lower().strip() == "employee":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigning a reporting manager is mandatory for employees."
                )

    employee = employee_service.update_employee(db, employee_id, request)
    return employee


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    # Auth check: must be Admin or HR
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to delete records"
        )

    # Get employee to check their role before deletion
    employee = employee_service.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Prevent self-deletion
    if current_user.id == employee.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-deletion is not permitted. Contact another administrator if you need to close your account."
        )

    # Get the target user's role
    target_user = db.query(User).filter(User.id == employee.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User account not found")

    current_role = current_user.role.name.lower()
    target_role = target_user.role.name.lower() if target_user.role else ""

    # Rule checks:
    # 1. Admin can delete anyone (except themselves, which is handled above)
    # 2. HR can only delete standard employees (cannot delete HR or Admin)
    if current_role == UserRole.HR:
        if target_role in [UserRole.HR, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR personnel are not authorized to delete HR or Admin accounts"
            )

    success = employee_service.delete_employee(db, employee_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete employee")

    return {"success": True, "message": "Employee deleted successfully"}


@router.get("/managers/all", response_model=list[EmployeeResponse])
def get_all_managers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to view managers"
        )
    return employee_service.get_all_managers(db)


@router.post("/{employee_id}/assign-manager", response_model=EmployeeResponse)
def assign_manager_role(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to assign manager role"
        )
    try:
        return employee_service.assign_manager_role(db, employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{employee_id}/revoke-manager", response_model=EmployeeResponse)
def revoke_manager_role(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to revoke manager role"
        )
    try:
        return employee_service.revoke_manager_role(db, employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{employee_id}/assign-team", response_model=list[EmployeeResponse])
def assign_team_to_manager(
    employee_id: int,
    payload: AssignTeamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to assign teams"
        )
    try:
        return employee_service.assign_team_to_manager(db, employee_id, payload.employee_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{employee_id}/team", response_model=list[EmployeeResponse])
def get_manager_team(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.name.lower() if current_user.role else ""
    if role not in [UserRole.ADMIN, UserRole.HR]:
        # If not admin/hr, can only view if current user is that manager
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp or emp.id != employee_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this team")
    return employee_service.get_manager_team(db, employee_id)


@router.post("/{employee_id}/change-code", response_model=EmployeeResponse)
def change_employee_code(
    employee_id: int,
    payload: ChangeEmployeeCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officially modify company employee code with required justification and audit logging."""
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to change employee codes",
        )
    try:
        changed_by = current_user.email or current_user.display_name or "ADMIN"
        return employee_code_service.change_employee_code(
            db=db,
            employee_id=employee_id,
            new_code=payload.new_employee_code,
            reason=payload.reason,
            changed_by=changed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{employee_id}/code-history", response_model=list[EmployeeCodeHistoryResponse])
def get_employee_code_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the full historical audit log of employee code changes."""
    role = current_user.role.name.lower() if current_user.role else ""
    if role not in [UserRole.ADMIN, UserRole.HR]:
        # Self-service check: employees can only view their own code history
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp or emp.id != employee_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this employee's code history")

    return employee_code_service.get_code_history_for_employee(db, employee_id)


@router.post("/{employee_id}/migrate-to-aivan-code", response_model=EmployeeResponse)
def migrate_to_aivan_code(
    employee_id: int,
    payload: MigrateToAivanCodeRequest = Body(default_factory=MigrateToAivanCodeRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Migrate an existing employee's code to the standardized AIVAN series."""
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to migrate employee codes",
        )
    try:
        changed_by = current_user.email or current_user.display_name or "HR"
        target_code = payload.new_employee_code if payload and payload.new_employee_code else None
        reason = (payload.reason if payload and payload.reason else "Standardized to official AIVAN series").strip()
        return employee_code_service.migrate_employee_to_aivan_code(
            db=db,
            employee_id=employee_id,
            target_code=target_code,
            reason=reason,
            changed_by=changed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bulk-migrate-to-aivan-codes")
def bulk_migrate_to_aivan_codes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk migrate all existing legacy employee codes to official AIVAN series."""
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to perform bulk code migrations",
        )
    changed_by = current_user.email or current_user.display_name or "SYSTEM"
    return employee_code_service.run_bulk_aivan_code_migration(db=db, changed_by=changed_by)

