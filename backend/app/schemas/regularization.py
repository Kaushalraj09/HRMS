from pydantic import BaseModel, ConfigDict, Field
from datetime import date, time, datetime
from typing import Optional, List

class RegularizationRequestCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attendance_date: date = Field(alias="attendanceDate")
    requested_punch_in: Optional[time] = Field(default=None, alias="requestedPunchIn")
    requested_punch_out: Optional[time] = Field(default=None, alias="requestedPunchOut")
    reason_type: str = Field(alias="reasonType")
    reason_text: str = Field(alias="reasonText")

class RegularizationRequestDecision(BaseModel):
    status: str # approved, rejected
    review_comment: Optional[str] = Field(default=None, alias="reviewComment")

class RegularizationRequestResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    employee_id: int = Field(alias="employeeId")
    employee_name: Optional[str] = Field(default=None, alias="employeeName")
    employee_code: Optional[str] = Field(default=None, alias="employeeCode")
    attendance_date: date = Field(alias="attendanceDate")
    requested_punch_in: Optional[time] = Field(default=None, alias="requestedPunchIn")
    requested_punch_out: Optional[time] = Field(default=None, alias="requestedPunchOut")
    reason_type: str = Field(alias="reasonType")
    reason_text: str = Field(alias="reasonText")
    status: str
    reviewed_by: Optional[int] = Field(default=None, alias="reviewedBy")
    reviewed_by_name: Optional[str] = Field(default=None, alias="reviewedByName")
    reviewed_at: Optional[datetime] = Field(default=None, alias="reviewedAt")
    review_comment: Optional[str] = Field(default=None, alias="reviewComment")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

class RegularizationRequestPaginatedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[RegularizationRequestResponse]
    page: int
    pageSize: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")
