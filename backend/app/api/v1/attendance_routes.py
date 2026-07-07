from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
import urllib.request
import json
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.core.enums import WorkMode, UserRole
from app.schemas.attendance import PunchRequest, ScheduleRequest, AttendanceResponse, AttendanceListResponse, TodayAttendanceState, EmployeeAnalytics, EmployeeLocationResponse
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.post("/punch-in", response_model=AttendanceResponse)
async def punch_in(
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
    
    from app.domain.attendance.services.punch_service import PunchService
    res = PunchService.punch_in(
        db,
        employee.id,
        request.work_mode,
        request.latitude,
        request.longitude,
        request.address,
        request.image,
        request.custom_time
    )

    return attendance_service.to_attendance_response(res, db)

@router.post("/punch-out", response_model=AttendanceResponse)
async def punch_out(
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
    
    from app.domain.attendance.services.punch_service import PunchService
    res = PunchService.punch_out(
        db,
        employee.id,
        request.work_mode,
        request.latitude,
        request.longitude,
        request.address,
        request.image,
        request.custom_time
    )

    return attendance_service.to_attendance_response(res, db)


@router.post("/me/punch", response_model=TodayAttendanceState)
async def punch_dynamic(
    request: PunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dynamic Punch In / Punch Out depending on active session state.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can punch attendance"
        )
    
    # Check today's state
    today_state = attendance_service.get_today_state(db, employee.id)
    
    if not today_state.get("punchIn"):
        await punch_in(request, db, current_user)
    else:
        await punch_out(request, db, current_user)
        
    return attendance_service.get_today_state(db, employee.id)


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

@router.post("/continue-working", response_model=TodayAttendanceState)
def continue_working(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Acknowledge shift end reminder and request overtime.
    This marks overtime_approved = True.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can use this endpoint"
        )
        
    # Get today's attendance record
    from datetime import datetime
    from zoneinfo import ZoneInfo
    APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
    current = datetime.now(APP_TIMEZONE)
    today = current.date()
    
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id, Attendance.date == today)
        .first()
    )
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active attendance record found for today"
        )
        
    attendance.overtime_approved = True
    attendance.overtime_start = datetime.strptime("18:00", "%H:%M").time()
    attendance.shift_end_reminder_sent = 3 # Acknowledged/dismissed
    
    # Recalculate metrics
    from app.services.attendance_service import calculate_attendance_metrics, log_audit_trail_sync
    calculate_attendance_metrics(attendance)
    db.commit()
    db.refresh(attendance)
    
    log_audit_trail_sync(db, "OVERTIME_CONTINUE", employee.id, f"Employee requested to continue working into overtime")
    
    return attendance_service.get_today_state(db, employee.id)

@router.post("/extend-overtime", response_model=TodayAttendanceState)
def extend_overtime(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Extend overtime at 20:00 to avoid auto-checkout.
    This sets overtime_extended = True and shifts the auto-checkout threshold.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can use this endpoint"
        )
        
    # Get today's attendance record
    from datetime import datetime
    from zoneinfo import ZoneInfo
    APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
    current = datetime.now(APP_TIMEZONE)
    today = current.date()
    
    attendance = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id, Attendance.date == today)
        .first()
    )
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active attendance record found for today"
        )
        
    attendance.overtime_extended = True
    attendance.overtime_reminder_sent = 3 # Acknowledged/dismissed
    
    from app.services.attendance_service import log_audit_trail_sync
    db.commit()
    db.refresh(attendance)
    
    log_audit_trail_sync(db, "OVERTIME_EXTEND", employee.id, f"Employee extended overtime at 20:00")
    
    return attendance_service.get_today_state(db, employee.id)

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
@router.get("/me/today", response_model=TodayAttendanceState)
def get_today_attendance_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        if current_user.role and current_user.role.name.lower() == "admin":
            from datetime import time
            return {
                "employeeId": None,
                "isWorking": False,
                "status": "Not Marked",
                "totalWorkedSeconds": 0,
                "approvedSeconds": 0,
                "remainingSeconds": 9 * 3600,
                "shiftTotalSeconds": 9 * 3600,
                "shiftElapsedSeconds": 0,
                "shiftStart": "09:00 AM",
                "shiftEnd": "06:00 PM",
                "workMode": "Office",
                "punchIn": None,
                "punchOut": None,
                "punchInLatitude": None,
                "punchInLongitude": None,
                "punchInAddress": None,
                "punchOutLatitude": None,
                "punchOutLongitude": None,
                "punchOutAddress": None,
                "punchInImage": None,
                "punchOutImage": None
            }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only employees can view attendance state"
        )

    return attendance_service.get_today_state(db, employee.id)

@router.get("/my-history", response_model=List[AttendanceResponse])
@router.get("/timesheet", response_model=List[AttendanceResponse])
@router.get("/me/timesheets", response_model=List[AttendanceResponse])
def get_my_history(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    status_filter: str = Query("", alias="status"),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get the attendance history for the logged-in employee.
    """
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        if current_user.role and current_user.role.name.lower() == "admin":
            return []
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only employees have attendance history"
        )
    records = attendance_service.get_my_history(
        db,
        employee.id,
        from_date=from_date,
        to_date=to_date,
        status_filter=status_filter,
    )
    return [attendance_service.to_attendance_response(r, db) for r in records]

@router.get("", response_model=AttendanceListResponse)
@router.get("/all", response_model=AttendanceListResponse)
def get_all_attendance_records(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    from_date: date | None = Query(None, alias="fromDate"),
    to_date: date | None = Query(None, alias="toDate"),
    search: str = "",
    department: str = "",
    status_filter: str = Query("", alias="status"),
    location: str = "",
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
        
    return attendance_service.list_all_attendance(
        db,
        page=page,
        limit=limit,
        from_date=from_date,
        to_date=to_date,
        search=search,
        department=department,
        status_filter=status_filter,
        location=location,
    )

@router.get("/ip-location")
def get_ip_location(request: Request, current_user: User = Depends(get_current_user)):
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

@router.get("/employee-analytics", response_model=List[EmployeeAnalytics])
def get_employee_analytics_dashboard(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get dynamic today's and monthly attendance analytics for each employee (HR and Admin only).
    """
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to view analytics"
        )
        
    return attendance_service.get_employee_analytics(db)


@router.get("/today-locations", response_model=List[EmployeeLocationResponse])
def get_today_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get locations of employees who punched in today (HR and Admin only).
    """
    if not current_user.role or current_user.role.name.lower() not in [UserRole.ADMIN.value, UserRole.HR.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view locations"
        )

    from datetime import date
    import random

    today = date.today()
    # Query today's attendance records where the user has punched in
    records = db.query(Attendance).join(Employee).filter(
        Attendance.date == today,
        Attendance.punch_in != None
    ).all()

    # Simple helper to extract city/state from address
    def extract_city_state(address: str):
        if not address:
            return "Unknown", "Unknown"
        parts = [p.strip() for p in address.split(',')]
        if len(parts) >= 3:
            return parts[-3], parts[-2]
        elif len(parts) == 2:
            return parts[0], parts[1]
        elif len(parts) == 1:
            return parts[0], "India"
        return "Unknown", "Unknown"

    city_coords = {
        "delhi": (28.6139, 77.2090),
        "new delhi": (28.6139, 77.2090),
        "mumbai": (19.0760, 72.8777),
        "bengaluru": (12.9716, 77.5946),
        "bangalore": (12.9716, 77.5946),
        "chennai": (13.0827, 80.2707),
        "kolkata": (22.5726, 88.3639),
        "hyderabad": (17.3850, 78.4867),
        "pune": (18.5204, 73.8567),
        "ahmedabad": (23.0225, 72.5714),
        "jaipur": (26.9124, 75.7873),
        "lucknow": (26.8467, 80.9462),
        "indore": (22.7196, 75.8577),
        "kochi": (9.9312, 76.2673),
    }

    response_data = []

    if not records:
        pass
    else:
        for r in records:
            emp = r.employee
            lat = r.punch_out_latitude or r.punch_in_latitude
            lon = r.punch_out_longitude or r.punch_in_longitude
            address = r.punch_out_address or r.punch_in_address or ""
            
            city, state = extract_city_state(address)
            
            # Match city in text if lat/lon not set
            if lat is None or lon is None:
                found = False
                addr_lower = address.lower()
                for name, coords in city_coords.items():
                    if name in addr_lower:
                        lat, lon = coords
                        city = name.title()
                        found = True
                        break
                if not found:
                    # Default center coordinates: New Delhi
                    lat, lon = (28.6139, 77.2090)
                    city, state = "New Delhi", "Delhi"

            # Parse status
            # Status can be ACTIVE, PUNCHED_OUT, LATE
            from app.services.time_calculator import calculate_late_minutes
            if r.punch_out is not None:
                status_val = "PUNCHED_OUT"
            elif r.punch_in is not None and (calculate_late_minutes(r.punch_in) > 0 or "LATE_ARRIVAL" in r.flags):
                status_val = "LATE"
            else:
                status_val = "ACTIVE"

            # Parse work mode: FIELD, OFFICE, REMOTE
            wm_lower = (r.work_mode or "").lower()
            if "office" in wm_lower:
                work_mode = "OFFICE"
            elif "remote" in wm_lower:
                work_mode = "REMOTE"
            else:
                work_mode = "FIELD"

            p_in = r.punch_in.strftime("%I:%M %p") if r.punch_in else None
            p_out = r.punch_out.strftime("%I:%M %p") if r.punch_out else None

            response_data.append(
                EmployeeLocationResponse(
                    employeeId=emp.id,
                    employeeName=f"{emp.first_name} {emp.last_name}",
                    latitude=lat,
                    longitude=lon,
                    city=city,
                    state=state,
                    punchInTime=p_in,
                    punchOutTime=p_out,
                    workMode=work_mode,
                    status=status_val
                )
            )

    return response_data


@router.get("/me/summary")
def get_me_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Only employees have attendance summaries")
        
    records = attendance_service.get_my_history(db, employee.id)
    
    total_days = len(records)
    computed_statuses = [
        attendance_service.get_attendance_status_with_timeoff(db, r.employee_id, r.punch_in, r.punch_out, r.date)
        for r in records
    ]
    worked_days = len([s for s in computed_statuses if s not in ["Not Marked", "Absent", "Time Off"]])
    present_days = len([s for s in computed_statuses if s in ["Present", "Half Day"]])
    working_days = len([s for s in computed_statuses if s == "Working"])
    absent_days = len([s for s in computed_statuses if s == "Absent"])
    not_marked_days = len([s for s in computed_statuses if s == "Not Marked"])
    
    return [
        { "label": "Total Days", "value": total_days, "icon": "fas fa-calendar total blue-icon" },
        { "label": "Worked Days", "value": worked_days, "icon": "fas fa-calendar-check worked blue-icon" },
        { "label": "Present", "value": present_days, "icon": "fas fa-check-circle blue-icon" },
        { "label": "Working", "value": working_days, "icon": "fas fa-user-check blue-icon" },
        { "label": "Absent", "value": absent_days, "icon": "fas fa-times-circle red-icon" },
        { "label": "Not Marked", "value": not_marked_days, "icon": "fas fa-user-times unapproved gold-icon" }
    ]


