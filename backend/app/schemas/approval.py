from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Literal

class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: Optional[str] = None
    approved_hours: Optional[float] = Field(None, alias="approvedHours")

    model_config = ConfigDict(populate_by_name=True)

class ApprovalItemResponse(BaseModel):
    id: int
    request_type: str = Field(..., alias="requestType")
    request_id: int = Field(..., alias="requestId")
    employee_id: int = Field(..., alias="employeeId")
    employee_name: str = Field(..., alias="employeeName")
    status: str
    submitted_at: datetime = Field(..., alias="submittedAt")
    priority: str
    assigned_role: str = Field("hr", alias="assignedRole")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

class ApprovalCounts(BaseModel):
    timeoff: int
    regularization: int
    total: int

class ApprovalQueueResponse(BaseModel):
    items: List[ApprovalItemResponse]
    counts: ApprovalCounts

class ApprovalTaskResponse(BaseModel):
    id: int
    request_type: str = Field(..., alias="requestType")
    request_id: int = Field(..., alias="requestId")
    employee_id: int = Field(..., alias="employeeId")
    assigned_role: str = Field(..., alias="assignedRole")
    status: str
    priority: str
    submitted_by: int = Field(..., alias="submittedBy")
    reviewed_by: Optional[int] = Field(None, alias="reviewedBy")
    reviewed_at: Optional[datetime] = Field(None, alias="reviewedAt")
    decision_comment: Optional[str] = Field(None, alias="decisionComment")
    created_at: datetime = Field(..., alias="createdAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
