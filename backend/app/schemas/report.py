from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Generic, TypeVar
from datetime import date, time, datetime

T = TypeVar("T")

class AttendanceSummaryRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employee_id: int = Field(alias="employeeId")
    employee_code: str = Field(alias="employeeCode")
    employee_name: str = Field(alias="employeeName")
    department: Optional[str] = Field(None, alias="department")
    present_days: int = Field(alias="presentDays")
    absent_days: int = Field(alias="absentDays")
    half_days: int = Field(alias="halfDays")
    leave_days: int = Field(alias="leaveDays")
    total_working_minutes: int = Field(alias="totalWorkingMinutes")
    total_overtime_minutes: int = Field(alias="totalOvertimeMinutes")

class LateArrivalRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employee_id: int = Field(alias="employeeId")
    employee_code: str = Field(alias="employeeCode")
    employee_name: str = Field(alias="employeeName")
    department: Optional[str] = Field(None, alias="department")
    date: date
    scheduled_start: Optional[time] = Field(None, alias="scheduledStart")
    punch_in: Optional[time] = Field(None, alias="punchIn")
    late_minutes: int = Field(alias="lateMinutes")

class MissingPunchRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employee_id: int = Field(alias="employeeId")
    employee_code: str = Field(alias="employeeCode")
    employee_name: str = Field(alias="employeeName")
    department: Optional[str] = Field(None, alias="department")
    date: date
    punch_in: Optional[time] = Field(None, alias="punchIn")
    punch_out: Optional[time] = Field(None, alias="punchOut")
    status: str
    reason: str

class LeaveUsageRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employee_id: int = Field(alias="employeeId")
    employee_code: str = Field(alias="employeeCode")
    employee_name: str = Field(alias="employeeName")
    department: Optional[str] = Field(None, alias="department")
    leave_type: str = Field(alias="leaveType")
    duration_hours: float = Field(alias="durationHours")
    date: date
    status: str
    reason: Optional[str] = Field(None, alias="reason")

class HrWorkloadRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    hr_name: str = Field(alias="hrName")
    pending_timeoff: int = Field(alias="pendingTimeoff")
    pending_regularization: int = Field(alias="pendingRegularization")
    processed_timeoff: int = Field(alias="processedTimeoff")
    processed_regularization: int = Field(alias="processedRegularization")
    total_handled: int = Field(alias="totalHandled")

class EmployeeStatusRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employee_id: int = Field(alias="employeeId")
    employee_code: str = Field(alias="employeeCode")
    employee_name: str = Field(alias="employeeName")
    department: Optional[str] = Field(None, alias="department")
    designation: Optional[str] = Field(None, alias="designation")
    status: str
    doj: Optional[date] = Field(None, alias="doj")
    timeoff_balance_hours: float = Field(alias="timeoffBalanceHours")

class LoginActivitySummaryRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    employee_id: Optional[int] = Field(None, alias="employeeId")
    employee_code: Optional[str] = Field(None, alias="employeeCode")
    employee_name: str = Field(alias="employeeName")
    email: str
    login_time: datetime = Field(alias="loginTime")
    ip_address: Optional[str] = Field(None, alias="ipAddress")
    browser: Optional[str] = Field(None, alias="browser")
    device: Optional[str] = Field(None, alias="device")
    operating_system: Optional[str] = Field(None, alias="operatingSystem")
    status: str

class PaginatedReportResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    pages: int
    data: List[T]
