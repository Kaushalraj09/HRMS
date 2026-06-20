from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.enums import UserRole
from app.schemas.report import (
    AttendanceSummaryRow,
    LateArrivalRow,
    MissingPunchRow,
    LeaveUsageRow,
    HrWorkloadRow,
    EmployeeStatusRow,
    LoginActivitySummaryRow,
    PaginatedReportResponse
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])

def check_role(user: User, allowed_roles: list[str]):
    if not user.role or user.role.name.lower() not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permissions for this resource."
        )

# HR Reports
@router.get("/hr/attendance-summary", response_model=PaginatedReportResponse[AttendanceSummaryRow])
def get_attendance_summary(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    department: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    export: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_role(current_user, ["admin", "hr"])
    
    export_all = (export == "csv")
    result = report_service.get_attendance_summary_report(
        db, start_date, end_date, department, search, page, limit, export_all=export_all
    )
    
    if export == "csv":
        headers = [
            "Employee Code", "Employee Name", "Department", "Present Days",
            "Absent Days", "Half Days", "Leave Days", "Total Working Hours", "Total Overtime Hours"
        ]
        rows = [
            [
                row["employeeCode"],
                row["employeeName"],
                row["department"] or "",
                str(row["presentDays"]),
                str(row["absentDays"]),
                str(row["halfDays"]),
                str(row["leaveDays"]),
                f"{row['totalWorkingMinutes'] / 60:.2f}",
                f"{row['totalOvertimeMinutes'] / 60:.2f}"
            ]
            for row in result["data"]
        ]
        return report_service.generate_report_csv(headers, rows, f"attendance_summary_{date.today().isoformat()}.csv")
        
    return result

@router.get("/hr/late-arrivals", response_model=PaginatedReportResponse[LateArrivalRow])
def get_late_arrivals(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    department: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    export: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_role(current_user, ["admin", "hr"])
    
    export_all = (export == "csv")
    result = report_service.get_late_arrival_report(
        db, start_date, end_date, department, search, page, limit, export_all=export_all
    )
    
    if export == "csv":
        headers = ["Employee Code", "Employee Name", "Department", "Date", "Scheduled Start", "Punch In", "Late Minutes"]
        rows = [
            [
                row["employeeCode"],
                row["employeeName"],
                row["department"] or "",
                row["date"].isoformat(),
                row["scheduledStart"].isoformat() if row["scheduledStart"] else "",
                row["punchIn"].isoformat() if row["punchIn"] else "",
                str(row["lateMinutes"])
            ]
            for row in result["data"]
        ]
        return report_service.generate_report_csv(headers, rows, f"late_arrivals_{date.today().isoformat()}.csv")
        
    return result

@router.get("/hr/missing-punches", response_model=PaginatedReportResponse[MissingPunchRow])
def get_missing_punches(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    department: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    export: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_role(current_user, ["admin", "hr"])
    
    export_all = (export == "csv")
    result = report_service.get_missing_punch_report(
        db, start_date, end_date, department, search, page, limit, export_all=export_all
    )
    
    if export == "csv":
        headers = ["Employee Code", "Employee Name", "Department", "Date", "Punch In", "Punch Out", "Status", "Reason"]
        rows = [
            [
                row["employeeCode"],
                row["employeeName"],
                row["department"] or "",
                row["date"].isoformat(),
                row["punchIn"].isoformat() if row["punchIn"] else "",
                row["punchOut"].isoformat() if row["punchOut"] else "",
                row["status"],
                row["reason"]
            ]
            for row in result["data"]
        ]
        return report_service.generate_report_csv(headers, rows, f"missing_punches_{date.today().isoformat()}.csv")
        
    return result

@router.get("/hr/leave-usage", response_model=PaginatedReportResponse[LeaveUsageRow])
def get_leave_usage(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    department: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    export: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_role(current_user, ["admin", "hr"])
    
    export_all = (export == "csv")
    result = report_service.get_leave_usage_report(
        db, start_date, end_date, department, search, page, limit, export_all=export_all
    )
    
    if export == "csv":
        headers = ["Employee Code", "Employee Name", "Department", "Date", "Leave Type", "Duration (Hours)", "Status", "Reason"]
        rows = [
            [
                row["employeeCode"],
                row["employeeName"],
                row["department"] or "",
                row["date"].isoformat(),
                row["leaveType"],
                f"{row['durationHours']:.1f}",
                row["status"],
                row["reason"] or ""
            ]
            for row in result["data"]
        ]
        return report_service.generate_report_csv(headers, rows, f"leave_usage_{date.today().isoformat()}.csv")
        
    return result

# Admin Reports
@router.get("/admin/hr-workload", response_model=PaginatedReportResponse[HrWorkloadRow])
def get_hr_workload(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    export: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_role(current_user, ["admin"])
    
    export_all = (export == "csv")
    result = report_service.get_hr_workload_report(
        db, start_date, end_date, page, limit, export_all=export_all
    )
    
    if export == "csv":
        headers = [
            "HR Name", "Pending Time-Off Requests", "Pending Regularizations",
            "Processed Time-Off Requests", "Processed Regularizations", "Total Handled"
        ]
        rows = [
            [
                row["hrName"],
                str(row["pendingTimeoff"]),
                str(row["pendingRegularization"]),
                str(row["processedTimeoff"]),
                str(row["processedRegularization"]),
                str(row["totalHandled"])
            ]
            for row in result["data"]
        ]
        return report_service.generate_report_csv(headers, rows, f"hr_workload_{date.today().isoformat()}.csv")
        
    return result

@router.get("/admin/employee-status", response_model=PaginatedReportResponse[EmployeeStatusRow])
def get_employee_status(
    department: Optional[str] = None,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    export: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_role(current_user, ["admin"])
    
    export_all = (export == "csv")
    result = report_service.get_employee_status_report(
        db, department, search, status_filter, page, limit, export_all=export_all
    )
    
    if export == "csv":
        headers = ["Employee Code", "Employee Name", "Department", "Designation", "Status", "DOJ", "Time-Off Balance (Hours)"]
        rows = [
            [
                row["employeeCode"],
                row["employeeName"],
                row["department"] or "",
                row["designation"] or "",
                row["status"],
                row["doj"].isoformat() if row["doj"] else "",
                f"{row['timeoffBalanceHours']:.1f}"
            ]
            for row in result["data"]
        ]
        return report_service.generate_report_csv(headers, rows, f"employee_status_{date.today().isoformat()}.csv")
        
    return result

@router.get("/admin/login-activity", response_model=PaginatedReportResponse[LoginActivitySummaryRow])
def get_login_activity(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    export: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_role(current_user, ["admin"])
    
    export_all = (export == "csv")
    result = report_service.get_login_activity_summary_report(
        db, start_date, end_date, page, limit, export_all=export_all
    )
    
    if export == "csv":
        headers = ["Employee Code", "Employee Name", "Email", "Login Time", "IP Address", "Browser", "Device", "OS", "Status"]
        rows = [
            [
                row["employeeCode"] or "",
                row["employeeName"],
                row["email"],
                row["loginTime"].strftime("%Y-%m-%d %I:%M %p"),
                row["ipAddress"] or "",
                row["browser"] or "",
                row["device"] or "",
                row["operatingSystem"] or "",
                row["status"]
            ]
            for row in result["data"]
        ]
        return report_service.generate_report_csv(headers, rows, f"login_activity_{date.today().isoformat()}.csv")
        
    return result
