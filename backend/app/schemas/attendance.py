from pydantic import BaseModel, ConfigDict, Field
from datetime import date, time, datetime
from typing import Optional, List

class PunchRequest(BaseModel):
    employee_id: Optional[int] = None
    workMode: str = "Office" # Office or Remote
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    image: Optional[str] = None  # base64 webcam snapshot

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
    punch_in_time: Optional[time] = Field(default=None, alias="punchInTime")
    punch_out_time: Optional[time] = Field(default=None, alias="punchOutTime")
    status: str
    work_mode: str = Field(alias="workMode")
    total_working_minutes: int = Field(default=0, alias="totalWorkingMinutes")
    overtime_minutes: int = Field(default=0, alias="overtimeMinutes")
    break_minutes: int = Field(default=0, alias="breakMinutes")
    grand_total_minutes: int = Field(default=0, alias="grandTotalMinutes")
    late_minutes: int = Field(default=0, alias="lateMinutes")

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
    punchInTime: Optional[time] = None
    punchOutTime: Optional[time] = None
    
    checkInLatitude: Optional[float] = Field(None, alias="checkInLatitude")
    checkInLongitude: Optional[float] = Field(None, alias="checkInLongitude")
    checkInAddress: Optional[str] = Field(None, alias="checkInAddress")
    checkOutLatitude: Optional[float] = Field(None, alias="checkOutLatitude")
    checkOutLongitude: Optional[float] = Field(None, alias="checkOutLongitude")
    checkOutAddress: Optional[str] = Field(None, alias="checkOutAddress")
    checkInImage: Optional[str] = Field(None, alias="checkInImage")
    checkOutImage: Optional[str] = Field(None, alias="checkOutImage")

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
    lateMinutes: int = 0
    workMode: Optional[str] = Field(None, alias="workMode")
    checkInAddress: Optional[str] = Field(None, alias="checkInAddress")
    checkOutAddress: Optional[str] = Field(None, alias="checkOutAddress")
    checkInImage: Optional[str] = Field(None, alias="checkInImage")
    checkOutImage: Optional[str] = Field(None, alias="checkOutImage")

class AttendanceListResponse(BaseModel):
    data: List[AttendanceRecord]
    total: int
