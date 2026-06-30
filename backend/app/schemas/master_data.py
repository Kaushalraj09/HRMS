from pydantic import BaseModel, Field
from datetime import date
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

    class Config:
        from_attributes = True

class DesignationBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True

class DesignationCreate(DesignationBase):
    pass

class DesignationResponse(DesignationBase):
    id: int

    class Config:
        from_attributes = True

class ShiftBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True

class ShiftCreate(ShiftBase):
    pass

class ShiftResponse(ShiftBase):
    id: int

    class Config:
        from_attributes = True

class WorkLocationBase(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True

class WorkLocationCreate(WorkLocationBase):
    pass

class WorkLocationResponse(WorkLocationBase):
    id: int

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

class MasterDataBootstrapResponse(BaseModel):
    departments: List[DepartmentResponse]
    designations: List[DesignationResponse]
    shifts: List[ShiftResponse]
    workLocations: List[WorkLocationResponse] = Field(..., alias="workLocations")
    leaveTypes: List[LeaveTypeResponse] = Field(..., alias="leaveTypes")

    class Config:
        populate_by_name = True
