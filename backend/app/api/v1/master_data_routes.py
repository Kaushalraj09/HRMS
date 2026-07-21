from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.master_data import (
    DepartmentCreate, DepartmentResponse,
    DesignationCreate, DesignationResponse,
    ShiftCreate, ShiftResponse,
    WorkLocationCreate, WorkLocationResponse,
    LeaveTypeCreate, LeaveTypeResponse,
    HolidayCreate, HolidayResponse,
    MasterDataBootstrapResponse
)
from app.services import master_data_service

router = APIRouter(prefix="/master-data", tags=["Master Data"])

def check_admin_hr(user: User):
    if not user.role or user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. HR or Admin privileges required."
        )

@router.get("/bootstrap", response_model=MasterDataBootstrapResponse)
def get_bootstrap(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return master_data_service.get_bootstrap_data(db)

# Department routes
@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.list_departments(db)

@router.post("/departments", response_model=DepartmentResponse)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.create_department(db, payload)

@router.put("/departments/{id}", response_model=DepartmentResponse)
def update_department(id: int, payload: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    dept = master_data_service.update_department(db, id, payload)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept

# Designation routes
@router.get("/designations", response_model=List[DesignationResponse])
def get_designations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.list_designations(db)

@router.post("/designations", response_model=DesignationResponse)
def create_designation(payload: DesignationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.create_designation(db, payload)

@router.put("/designations/{id}", response_model=DesignationResponse)
def update_designation(id: int, payload: DesignationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    desig = master_data_service.update_designation(db, id, payload)
    if not desig:
        raise HTTPException(status_code=404, detail="Designation not found")
    return desig

# Shift routes
@router.get("/shifts", response_model=List[ShiftResponse])
def get_shifts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.list_shifts(db)

@router.post("/shifts", response_model=ShiftResponse)
def create_shift(payload: ShiftCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.create_shift(db, payload)

@router.put("/shifts/{id}", response_model=ShiftResponse)
def update_shift(id: int, payload: ShiftCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    shift = master_data_service.update_shift(db, id, payload)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift

# WorkLocation routes
@router.get("/work-locations", response_model=List[WorkLocationResponse])
def get_work_locations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.list_work_locations(db)

@router.post("/work-locations", response_model=WorkLocationResponse)
def create_work_location(payload: WorkLocationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.create_work_location(db, payload)

@router.put("/work-locations/{id}", response_model=WorkLocationResponse)
def update_work_location(id: int, payload: WorkLocationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    loc = master_data_service.update_work_location(db, id, payload)
    if not loc:
        raise HTTPException(status_code=404, detail="Work location not found")
    return loc

# LeaveType routes
@router.get("/leave-types", response_model=List[LeaveTypeResponse])
def get_leave_types(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.list_leave_types(db)

@router.post("/leave-types", response_model=LeaveTypeResponse)
def create_leave_type(payload: LeaveTypeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.create_leave_type(db, payload)

@router.put("/leave-types/{id}", response_model=LeaveTypeResponse)
def update_leave_type(id: int, payload: LeaveTypeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    lt = master_data_service.update_leave_type(db, id, payload)
    if not lt:
        raise HTTPException(status_code=404, detail="Leave type not found")
    return lt

# Holiday routes
@router.get("/holidays", response_model=List[HolidayResponse])
def get_holidays(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.list_holidays(db)

@router.post("/holidays", response_model=HolidayResponse)
def create_holiday(payload: HolidayCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    return master_data_service.create_holiday(db, payload)

@router.put("/holidays/{id}", response_model=HolidayResponse)
def update_holiday(id: int, payload: HolidayCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_hr(current_user)
    h = master_data_service.update_holiday(db, id, payload)
    if not h:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return h
