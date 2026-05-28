from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from datetime import date, time, datetime
from typing import Optional, List
from app.core.enums import WorkMode


class PunchRequest(BaseModel):
    """Request model for punch in/out operations with optional location/image data."""
    model_config = ConfigDict(populate_by_name=True)

    employee_id: Optional[int] = Field(
        default=None,
        alias="employeeId",
        validation_alias=AliasChoices("employeeId", "employee_id"),
    )
    work_mode: WorkMode = Field(default=WorkMode.office, alias="workMode")
    latitude: Optional[float] = Field(default=None, description="Optional check-in/out latitude")
    longitude: Optional[float] = Field(default=None, description="Optional check-in/out longitude")
    address: Optional[str] = Field(default=None, description="Optional check-in/out address")
    image: Optional[str] = Field(default=None, description="Optional base64 encoded webcam snapshot")
    custom_time: Optional[datetime] = Field(
        default=None,
        alias="customTime",
        validation_alias=AliasChoices(
            "customTime",
            "punchInTime",
            "punchOutTime",
            "punch_in_time",
            "punch_out_time",
        ),
    )

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: Optional[str]) -> Optional[str]:
        """Validate image size - max 5MB for base64."""
        if value and len(value) > 5_000_000:
            raise ValueError("Image too large (max 5MB)")
        return value

    @field_validator("work_mode", mode="before")
    @classmethod
    def validate_work_mode(cls, value):
        """Convert string work mode to enum."""
        if isinstance(value, str):
            try:
                return WorkMode(value)
            except ValueError:
                raise ValueError(f"Invalid work mode. Must be one of: {', '.join([m.value for m in WorkMode])}")
        return value

class ScheduleRequest(BaseModel):
    """Request model for scheduling shifts."""
    model_config = ConfigDict(populate_by_name=True)

    date: date
    start_time: Optional[time] = Field(default=None, alias="startTime")
    end_time: Optional[time] = Field(default=None, alias="endTime")
    work_mode: WorkMode = Field(default=WorkMode.office, alias="workMode")
    task_description: Optional[str] = Field(default=None, alias="taskDescription")

    @field_validator("work_mode", mode="before")
    @classmethod
    def validate_work_mode(cls, value):
        """Convert string work mode to enum."""
        if isinstance(value, str):
            try:
                return WorkMode(value)
            except ValueError:
                raise ValueError(f"Invalid work mode. Must be one of: {', '.join([m.value for m in WorkMode])}")
        return value

class AttendanceResponse(BaseModel):
    """Complete attendance record response with all calculated metrics."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            time: lambda v: v.isoformat() if v else None,
        }
    )

    id: int
    employee_id: int = Field(alias="employeeId")
    date: date
    scheduled_start: Optional[time] = Field(default=None, alias="scheduledStart")
    scheduled_end: Optional[time] = Field(default=None, alias="scheduledEnd")
    task_description: Optional[str] = Field(default=None, alias="taskDescription")
    check_in: Optional[time] = Field(default=None, alias="punchIn")
    check_out: Optional[time] = Field(default=None, alias="punchOut")
    status: str
    work_mode: WorkMode = Field(alias="workMode")
    
    # Location fields - optional
    check_in_latitude: Optional[float] = Field(default=None, alias="punchInLatitude")
    check_in_longitude: Optional[float] = Field(default=None, alias="punchInLongitude")
    check_in_address: Optional[str] = Field(default=None, alias="punchInAddress")
    check_out_latitude: Optional[float] = Field(default=None, alias="punchOutLatitude")
    check_out_longitude: Optional[float] = Field(default=None, alias="punchOutLongitude")
    check_out_address: Optional[str] = Field(default=None, alias="punchOutAddress")
    
    # Image fields - optional
    check_in_image: Optional[str] = Field(default=None, alias="punchInImage")
    check_out_image: Optional[str] = Field(default=None, alias="punchOutImage")
    
    # Calculated metrics
    total_working_minutes: int = Field(default=0, alias="totalWorkingMinutes")
    overtime_minutes: int = Field(default=0, alias="overtimeMinutes")
    break_minutes: int = Field(default=0, alias="breakMinutes")
    grand_total_minutes: int = Field(default=0, alias="grandTotalMinutes")
    late_minutes: int = Field(default=0, alias="lateMinutes")

class TodayAttendanceState(BaseModel):
    """Current attendance state for today with working metrics and shift information."""
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            time: lambda v: v.isoformat() if v else None,
        }
    )

    employee_id: Optional[int] = Field(default=None, alias="employeeId")
    is_working: bool = Field(alias="isWorking")
    status: str
    total_worked_seconds: int = Field(alias="totalWorkedSeconds")
    approved_seconds: int = Field(alias="approvedSeconds")
    remaining_seconds: int = Field(alias="remainingSeconds")
    shift_total_seconds: int = Field(alias="shiftTotalSeconds")
    shift_elapsed_seconds: int = Field(alias="shiftElapsedSeconds")
    shift_start: str = Field(alias="shiftStart")
    shift_end: str = Field(alias="shiftEnd")
    work_mode: WorkMode = Field(default=WorkMode.office)
    
    # Optional punch times and location
    punch_in: Optional[time] = Field(default=None, alias="punchIn")
    punch_out: Optional[time] = Field(default=None, alias="punchOut")
    punch_in_latitude: Optional[float] = Field(default=None, alias="punchInLatitude")
    punch_in_longitude: Optional[float] = Field(default=None, alias="punchInLongitude")
    punch_in_address: Optional[str] = Field(default=None, alias="punchInAddress")
    punch_out_latitude: Optional[float] = Field(default=None, alias="punchOutLatitude")
    punch_out_longitude: Optional[float] = Field(default=None, alias="punchOutLongitude")
    punch_out_address: Optional[str] = Field(default=None, alias="punchOutAddress")
    
    # Optional images
    punch_in_image: Optional[str] = Field(default=None, alias="punchInImage")
    punch_out_image: Optional[str] = Field(default=None, alias="punchOutImage")

class AttendanceRecord(BaseModel):
    """Attendance record for list responses."""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    employee_name: str = Field(alias="employeeName")
    employee_code: str = Field(alias="employeeCode")
    department: str
    date: date
    scheduled_start: Optional[time] = Field(default=None, alias="scheduledStart")
    scheduled_end: Optional[time] = Field(default=None, alias="scheduledEnd")
    task_description: Optional[str] = Field(default=None, alias="taskDescription")
    punch_in: Optional[time] = Field(default=None, alias="punchIn")
    punch_out: Optional[time] = Field(default=None, alias="punchOut")
    status: str
    total_working_minutes: int = Field(default=0, alias="totalWorkingMinutes")
    overtime_minutes: int = Field(default=0, alias="overtimeMinutes")
    break_minutes: int = Field(default=0, alias="breakMinutes")
    grand_total_minutes: int = Field(default=0, alias="grandTotalMinutes")
    late_minutes: int = Field(default=0, alias="lateMinutes")
    work_mode: Optional[WorkMode] = Field(None, alias="workMode")
    punch_in_address: Optional[str] = Field(default=None, alias="punchInAddress")
    punch_out_address: Optional[str] = Field(default=None, alias="punchOutAddress")
    punch_in_image: Optional[str] = Field(default=None, alias="punchInImage")
    punch_out_image: Optional[str] = Field(default=None, alias="punchOutImage")


class AttendanceListResponse(BaseModel):
    """List response for all attendance records."""
    data: List[AttendanceRecord]
    total: int
