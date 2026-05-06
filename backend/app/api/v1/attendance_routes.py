from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
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
    Punch In for the current employee.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only employees can punch attendance"
        )
    
    return attendance_service.punch_in(db, employee.id, request.workMode)

@router.post("/punch-out", response_model=AttendanceResponse)
def punch_out(
    request: PunchRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Punch Out for the current employee.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only employees can punch attendance"
        )
    
    return attendance_service.punch_out(db, employee.id, request.workMode)

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
        start_time=request.startTime,
        end_time=request.endTime,
        work_mode=request.workMode,
        task_description=request.taskDescription
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
