from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.employee import EmployeeCreate, EmployeeCredentialsResponse, EmployeeResponse, EmployeeUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employee-management"])

@router.post("", response_model=EmployeeResponse)
def add_employee(request: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        return employee_service.create_employee(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("", response_model=List[EmployeeResponse])
def get_all_employees(db: Session = Depends(get_db)):
    return employee_service.list_employees(db)

@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    employee = employee_service.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@router.get("/{employee_id}/credentials", response_model=EmployeeCredentialsResponse)
def get_employee_credentials(employee_id: int, db: Session = Depends(get_db)):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    credentials = employee_service.get_employee_credentials(db, employee_id)
    if not credentials:
        raise HTTPException(status_code=404, detail="Employee credentials not found")
    return credentials

@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, request: EmployeeUpdate, db: Session = Depends(get_db)):
    if employee_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    employee = employee_service.update_employee(db, employee_id, request)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
