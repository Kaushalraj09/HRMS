from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.employee import EmployeeCreate, EmployeeResponse
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employee-management"])

@router.post("", response_model=EmployeeResponse)
def add_employee(request: EmployeeCreate, db: Session = Depends(get_db)):
    return employee_service.create_employee(db, request)

@router.get("", response_model=List[EmployeeResponse])
def get_all_employees(db: Session = Depends(get_db)):
    return employee_service.list_employees(db)
