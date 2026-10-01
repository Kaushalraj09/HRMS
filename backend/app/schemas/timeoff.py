from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from datetime import date, time, datetime
from typing import Optional, Literal

class TimeOffRequestCreate(BaseModel):
    date: date
    leave_type: str # Full-Day, Half-Day
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: float
    reason: Optional[str] = None
    attachment_name: Optional[str] = None
    batch_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_days: Optional[float] = None

class TimeOffBatchRequestCreate(BaseModel):
    dates: list[date]
    leave_type: str
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: float
    reason: Optional[str] = None
    attachment_name: Optional[str] = None

class TimeOffRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_code: Optional[str] = None
    date: date
    leave_type: str
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: float
    status: str
    employee_name: Optional[str] = None
    reason: Optional[str] = None
    attachment_name: Optional[str] = None
    batch_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_days: Optional[float] = None
    approval_stage: Optional[str] = "Manager"
    manager_name: Optional[str] = None
    manager_decision: Optional[str] = None
    manager_comment: Optional[str] = None
    manager_reviewed_at: Optional[datetime] = None
    hr_reviewed_at: Optional[datetime] = None
    hr_comment: Optional[str] = None

class TimeOffBatchResponse(BaseModel):
    created_requests: list[TimeOffRequestResponse]


class TimeOffApplyPayload(BaseModel):
    """Inline apply: backend derives duration from times or full-day rule."""

    date: date
    leave_type: str  # "Half-Day" | "Full Day" (also accepts "Full-Day")
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class TimeOffApplyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_code: Optional[str] = None
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
    employee_name: Optional[str] = None

class TimeOffRequestPaginatedResponse(BaseModel):
    items: list[TimeOffRequestResponse]
    page: int
    pageSize: int
    totalItems: int
    totalPages: int


class TimeOffDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: Optional[str] = None
    approvedHours: Optional[float] = None
