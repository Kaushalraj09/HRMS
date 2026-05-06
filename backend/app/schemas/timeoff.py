from pydantic import BaseModel, ConfigDict
from datetime import date, time
from typing import Optional

class TimeOffRequestCreate(BaseModel):
    date: date
    leave_type: str # Full-Day, Half-Day, Hourly
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: float

class TimeOffRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    date: date
    leave_type: str
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: float
    status: str


class TimeOffApplyPayload(BaseModel):
    """Inline apply: backend derives duration from times or full-day rule."""

    date: date
    leave_type: str  # "Hourly" | "Full Day" (also accepts "Full-Day")
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class TimeOffApplyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    date: date
    leave_type: str
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: float
    status: str
    approved_hours_today: float
    remaining_hours_today: float
    approved_seconds_today: int
    remaining_seconds_today: int
