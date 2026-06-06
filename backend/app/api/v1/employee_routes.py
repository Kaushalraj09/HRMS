from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.enums import UserRole
from app.schemas.employee import EmployeeCreate, EmployeeCredentialsResponse, EmployeeResponse, EmployeeUpdate
from app.services import employee_service

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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("", response_model=List[EmployeeResponse])
def get_all_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to view all employees"
        )
    return employee_service.list_employees(db)

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

@router.get("/{employee_id}/credentials", response_model=EmployeeCredentialsResponse)
def get_employee_credentials(
    employee_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to view employee credentials"
        )

    credentials = employee_service.get_employee_credentials(db, employee_id)
    if not credentials:
        raise HTTPException(status_code=404, detail="Employee credentials not found")
    return credentials

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

