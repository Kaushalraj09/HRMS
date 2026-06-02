from fastapi import APIRouter, Depends, HTTPException, status, Request
import urllib.request
import json
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.core.enums import WorkMode
from app.schemas.attendance import PunchRequest, ScheduleRequest, AttendanceResponse, AttendanceListResponse, TodayAttendanceState
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.post("/punch-in", response_model=AttendanceResponse)
def punch_in(
    request: PunchRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Punch In for the current employee or specified employee.
    """
    if request.employee_id:
        employee = db.query(Employee).filter(Employee.id == request.employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {request.employee_id} not found"
            )
    else:
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only employees can punch attendance"
            )
    
    return attendance_service.punch_in(
        db,
        employee.id,
        request.work_mode,
        request.latitude,
        request.longitude,
        request.address,
        request.image,
        request.custom_time
    )

@router.post("/punch-out", response_model=AttendanceResponse)
def punch_out(
    request: PunchRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Punch Out for the current employee or specified employee.
    """
    if request.employee_id:
        employee = db.query(Employee).filter(Employee.id == request.employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {request.employee_id} not found"
            )
    else:
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only employees can punch attendance"
            )
    
    return attendance_service.punch_out(
        db,
        employee.id,
        request.work_mode,
        request.latitude,
        request.longitude,
        request.address,
        request.image,
        request.custom_time
    )

class ChangeWorkModeRequest(BaseModel):
    work_mode: WorkMode = Field(alias="workMode")

@router.post("/work-mode", response_model=TodayAttendanceState)
def change_work_mode(
    request: ChangeWorkModeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the work mode (Office/Remote) for today's active session or pre-punch state.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can change work mode"
        )
    
    return attendance_service.update_today_work_mode(db, employee.id, request.work_mode)

@router.post("/schedule", response_model=AttendanceResponse)
def add_schedule(
    request: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Schedule a future shift for the current employee.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can schedule shifts"
        )
    
    return attendance_service.add_schedule(
        db=db,
        employee_id=employee.id,
        schedule_date=request.date,
        start_time=request.start_time,
        end_time=request.end_time,
        work_mode=request.work_mode,
        task_description=request.task_description
    )

@router.get("/today", response_model=TodayAttendanceState)
@router.get("/today-state", response_model=TodayAttendanceState)
def get_today_attendance_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can view attendance state"
        )

    return attendance_service.get_today_state(db, employee.id)

@router.get("/my-history", response_model=List[AttendanceResponse])
@router.get("/timesheet", response_model=List[AttendanceResponse])
def get_my_history(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get the attendance history for the logged-in employee.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only employees have attendance history"
        )
    records = attendance_service.get_my_history(db, employee.id)
    return [attendance_service.to_attendance_response(r) for r in records]

@router.get("/all", response_model=AttendanceListResponse)
def get_all_attendance_records(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get all attendance records for monitoring (HR and Admin only).
    """
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to view all records"
        )
        
    return attendance_service.list_all_attendance(db)

@router.get("/ip-location")
def get_ip_location(request: Request):
    """
    Proxy endpoint to fetch IP-based location, bypassing browser CORS issues.
    """
    client_host = request.client.host
    url = "https://freeipapi.com/api/json"
    if client_host and client_host not in ["127.0.0.1", "::1", "localhost"] and not client_host.startswith("192.168.") and not client_host.startswith("10."):
        url = f"https://freeipapi.com/api/json/{client_host}"
        
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {
            "latitude": None,
            "longitude": None,
            "cityName": "",
            "regionName": "",
            "countryName": ""
        }
