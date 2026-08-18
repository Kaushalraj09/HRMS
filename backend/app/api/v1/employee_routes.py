from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.core.enums import UserRole
from app.schemas.employee import EmployeeCreate, EmployeeCredentialsResponse, EmployeeListResponse, EmployeeResponse, EmployeeUpdate
from app.services import employee_service
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
    try:
        return employee_service.create_employee(db, request)
    except InvitationDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("", response_model=EmployeeListResponse)
def get_all_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
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
        "temporary_password_hint": "Use Reset Access to send a secure password setup email. Passwords are never displayed.",
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

    # Trigger password reset by email. Credentials never leave the server.
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
        "temporary_password_hint": "Password setup email sent. No password is displayed or stored in readable form.",
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

    employee = employee_service.update_employee(db, employee_id, request)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
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
