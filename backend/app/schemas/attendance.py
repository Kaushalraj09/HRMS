from pydantic import BaseModel, ConfigDict, Field
from datetime import date, time, datetime
from typing import Optional, List

class PunchRequest(BaseModel):
    employee_id: Optional[int] = None
    workMode: str = "Office" # Office or Remote

class ScheduleRequest(BaseModel):
    date: date
    startTime: Optional[time] = None
    endTime: Optional[time] = None
    workMode: str = "Office"
    taskDescription: Optional[str] = None

class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    date: date
    scheduled_start: Optional[time] = Field(default=None, alias="scheduledStart")
    scheduled_end: Optional[time] = Field(default=None, alias="scheduledEnd")
    task_description: Optional[str] = Field(default=None, alias="taskDescription")
    check_in: Optional[time] = Field(default=None, alias="checkIn")
    check_out: Optional[time] = Field(default=None, alias="checkOut")
    status: str
    work_mode: str = Field(alias="workMode")
    total_working_minutes: int = Field(default=0, alias="totalWorkingMinutes")
    overtime_minutes: int = Field(default=0, alias="overtimeMinutes")
    break_minutes: int = Field(default=0, alias="breakMinutes")
    grand_total_minutes: int = Field(default=0, alias="grandTotalMinutes")

class TodayAttendanceState(BaseModel):
    isWorking: bool = Field(alias="isWorking")
    status: str
    totalWorkedSeconds: int = Field(alias="totalWorkedSeconds")
    approvedSeconds: int = Field(alias="approvedSeconds")
    remainingSeconds: int = Field(alias="remainingSeconds")
    shiftTotalSeconds: int = Field(alias="shiftTotalSeconds")
    shiftElapsedSeconds: int = Field(alias="shiftElapsedSeconds")
    shiftStart: str = Field(alias="shiftStart")
    shiftEnd: str = Field(alias="shiftEnd")
    workMode: str = "Office"
    checkIn: Optional[time] = None
    checkOut: Optional[time] = None

class AttendanceRecord(BaseModel):
    id: int
    employeeName: str
    employeeCode: str
    department: str
    date: date
    scheduledStart: Optional[time] = None
    scheduledEnd: Optional[time] = None
    taskDescription: Optional[str] = None
    checkIn: Optional[time] = None
    checkOut: Optional[time] = None
    status: str
    totalWorkingMinutes: int = 0
    overtimeMinutes: int = 0
    breakMinutes: int = 0
    grandTotalMinutes: int = 0

class AttendanceListResponse(BaseModel):
    data: List[AttendanceRecord]
    total: int
