from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import date, time
from typing import Optional, List

class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class DesignationBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True

class DesignationCreate(DesignationBase):
    pass

class DesignationResponse(DesignationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ShiftBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    working_hours: float = 8.0
    required_work_minutes: int = 480
    grace_minutes: int = 30
    lunch_duration_minutes: Optional[int] = 40
    lunch_start_time: Optional[time] = None
    lunch_end_time: Optional[time] = None
    half_day_hours: float = 4.0
    minimum_half_day_minutes: int = 240
    present_hours: float = 8.0
    minimum_present_minutes: int = 480
    overtime_start_time: Optional[time] = None
    overtime_allowed: bool = True
    max_overtime_minutes: Optional[int] = 120
    late_mark_after_minutes: int = 30
    early_exit_before_minutes: int = 0
    is_night_shift: bool = False
    timezone: str = "Asia/Kolkata"
    is_active: bool = True
    
    # New Attendance Rules
    allow_early_punch_in: Optional[bool] = False
    early_coming_minutes: Optional[int] = 60
    punch_in_grace_minutes: Optional[int] = 10
    shift_grace_minutes: Optional[int] = 15

    @field_validator(
        "lunch_start_time",
        "lunch_end_time",
        "overtime_start_time",
        "start_time",
        "end_time",
        "description",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

class ShiftCreate(ShiftBase):
    pass

class ShiftResponse(ShiftBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class WorkLocationBase(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    location_type: Optional[str] = Field(default="office", alias="location_type")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius_meters: Optional[float] = Field(default=40.0, alias="geofence_radius_meters")
    is_active: bool = True

class WorkLocationCreate(WorkLocationBase):
    pass

class WorkLocationResponse(WorkLocationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class LeaveTypeBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=30)
    unit_type: str = Field("full_day", max_length=20)
    default_balance_hours: float = 0.0
    requires_approval: bool = True
    is_active: bool = True

class LeaveTypeCreate(LeaveTypeBase):
    pass

class LeaveTypeResponse(LeaveTypeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class HolidayBase(BaseModel):
    holiday_date: date
    name: str = Field(..., max_length=120)
    description: Optional[str] = Field(None, max_length=255)
    is_optional: bool = False
    is_active: bool = True

class HolidayCreate(HolidayBase):
    pass

class HolidayResponse(HolidayBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class MasterDataBootstrapResponse(BaseModel):
    departments: List[DepartmentResponse]
    designations: List[DesignationResponse]
    shifts: List[ShiftResponse]
    workLocations: List[WorkLocationResponse] = Field(..., alias="workLocations")
    leaveTypes: List[LeaveTypeResponse] = Field(..., alias="leaveTypes")
    holidays: List[HolidayResponse] = []

    model_config = ConfigDict(populate_by_name=True)
