from pydantic import BaseModel, ConfigDict, Field
from datetime import date, time, datetime
from typing import Optional, List

class PunchRequest(BaseModel):
    workMode: str = "Office" # Office or Remote

class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    date: date
    checkIn: Optional[time] = Field(default=None, alias="check_in")
    checkOut: Optional[time] = Field(default=None, alias="check_out")
    status: str
    workMode: str = Field(alias="work_mode")

class TodayAttendanceState(BaseModel):
    isPunchedIn: bool
    status: str
    checkIn: Optional[time] = None
    checkOut: Optional[time] = None
    workMode: str = "Office"

class AttendanceRecord(BaseModel):
    id: int
    employeeName: str
    employeeCode: str
    department: str
    date: date
    checkIn: Optional[time] = None
    checkOut: Optional[time] = None
    status: str

class AttendanceListResponse(BaseModel):
    data: List[AttendanceRecord]
    total: int
