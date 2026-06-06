from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, computed_field
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
    punch_in: Optional[time] = Field(default=None, alias="punchIn")
    punch_out: Optional[time] = Field(default=None, alias="punchOut")
    status: str
    work_mode: WorkMode = Field(alias="workMode")
    
    # Location fields - optional
    punch_in_latitude: Optional[float] = Field(default=None, alias="punchInLatitude")
    punch_in_longitude: Optional[float] = Field(default=None, alias="punchInLongitude")
    punch_in_address: Optional[str] = Field(default=None, alias="punchInAddress")
    punch_out_latitude: Optional[float] = Field(default=None, alias="punchOutLatitude")
    punch_out_longitude: Optional[float] = Field(default=None, alias="punchOutLongitude")
    punch_out_address: Optional[str] = Field(default=None, alias="punchOutAddress")
    
    # Image fields - optional
    punch_in_image: Optional[str] = Field(default=None, alias="punchInImage")
    punch_out_image: Optional[str] = Field(default=None, alias="punchOutImage")
    
    # Calculated metrics
    total_working_minutes: int = Field(default=0, alias="totalWorkingMinutes")
    overtime_minutes: int = Field(default=0, alias="overtimeMinutes")
    break_minutes: int = Field(default=0, alias="breakMinutes")
    grand_total_minutes: int = Field(default=0, alias="grandTotalMinutes")
    late_minutes: int = Field(default=0, alias="lateMinutes")
    early_exit_minutes: int = Field(default=0, alias="earlyExitMinutes")

    @computed_field(alias="isWorking")
    @property
    def is_working(self) -> bool:
        return self.status.lower() == "working"

    @computed_field(alias="attendanceStatus")
    @property
    def attendance_status(self) -> str:
        return self.status.lower()

    @computed_field(alias="badgeColor")
    @property
    def badge_color(self) -> str:
        return "green" if self.status.lower() == "working" else "gray"

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
    work_mode: WorkMode = Field(default=WorkMode.office, alias="workMode")
    
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

    @computed_field(alias="attendanceStatus")
    @property
    def attendance_status(self) -> str:
        return self.status.lower()

    @computed_field(alias="badgeColor")
    @property
    def badge_color(self) -> str:
        return "green" if self.status.lower() == "working" else "gray"

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
    early_exit_minutes: int = Field(default=0, alias="earlyExitMinutes")
    work_mode: Optional[WorkMode] = Field(None, alias="workMode")
    punch_in_address: Optional[str] = Field(default=None, alias="punchInAddress")
    punch_out_address: Optional[str] = Field(default=None, alias="punchOutAddress")
    punch_in_image: Optional[str] = Field(default=None, alias="punchInImage")
    punch_out_image: Optional[str] = Field(default=None, alias="punchOutImage")

    @computed_field(alias="isWorking")
    @property
    def is_working(self) -> bool:
        return self.status.lower() == "working"

    @computed_field(alias="attendanceStatus")
    @property
    def attendance_status(self) -> str:
        return self.status.lower()

    @computed_field(alias="badgeColor")
    @property
    def badge_color(self) -> str:
        return "green" if self.status.lower() == "working" else "gray"


class AttendanceListResponse(BaseModel):
    """List response for all attendance records."""
    data: List[AttendanceRecord]
    total: int

class TodayAnalytics(BaseModel):
    punch_in: Optional[str] = Field(default=None, alias="punchIn")
    punch_out: Optional[str] = Field(default=None, alias="punchOut")
    status: str
    working_hours: str = Field(alias="workingHours")

class MonthlyAnalytics(BaseModel):
    present_days: int = Field(alias="presentDays")
    absent_days: int = Field(alias="absentDays")
    half_days: int = Field(alias="halfDays")
    late_count: int = Field(alias="lateCount")
    total_working_hours: str = Field(alias="totalWorkingHours")
    total_overtime: str = Field(alias="totalOvertime")
    attendance_percentage: float = Field(alias="attendancePercentage")

class EmployeeAnalytics(BaseModel):
    employee_id: int = Field(alias="employeeId")
    employee_name: str = Field(alias="employeeName")
    employee_code: str = Field(alias="employeeCode")
    department: str
    today: TodayAnalytics
    monthly: MonthlyAnalytics
