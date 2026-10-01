from pydantic import BaseModel, EmailStr, field_serializer, ConfigDict
from typing import Optional, List
from datetime import date, datetime

from app.utils.employee_code import normalize_employee_code

from app.schemas.master_data import ShiftResponse

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    gender: Optional[str] = None
    dob: Optional[date] = None
    marital_status: Optional[str] = None
    blood_group: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employee_type: Optional[str] = None
    work_location: Optional[str] = None
    shift_type: Optional[str] = None
    shift_id: Optional[int] = None
    doj: Optional[date] = None
    official_email: EmailStr
    personal_email: Optional[EmailStr] = None
    mobile: str
    alternate_mobile: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    status: str = "Active"

    # Banking & Statutory Info
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    ifsc_code: Optional[str] = None
    micr_code: Optional[str] = None
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None
    pf_number: Optional[str] = None
    legacy_employee_code: Optional[str] = None
    employee_code: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    reporting_manager_id: Optional[int] = None
    role: Optional[str] = None

class EmployeeUpdate(BaseModel):
    reporting_manager_id: Optional[int] = None
    role: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    marital_status: Optional[str] = None
    blood_group: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employee_type: Optional[str] = None
    work_location: Optional[str] = None
    shift_type: Optional[str] = None
    shift_id: Optional[int] = None
    doj: Optional[date] = None
    official_email: Optional[EmailStr] = None
    personal_email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    alternate_mobile: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    status: Optional[str] = None

    # Banking & Statutory Info
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    ifsc_code: Optional[str] = None
    micr_code: Optional[str] = None
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None
    pf_number: Optional[str] = None
    legacy_employee_code: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    id: int
    user_id: int
    employee_id: Optional[int] = None
    employee_code: str
    reporting_manager_id: Optional[int] = None
    reporting_manager_name: Optional[str] = None
    user_role: Optional[str] = "Employee"
    is_manager: Optional[bool] = False
    direct_reports_count: Optional[int] = 0
    shift: Optional[ShiftResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer("employee_code")
    def _serialize_employee_code(self, value: str) -> str:
        return normalize_employee_code(value)

    model_config = ConfigDict(from_attributes=True)

    def __init__(self, **data):
        super().__init__(**data)
        if self.employee_id is None:
            self.employee_id = self.id


class AssignTeamRequest(BaseModel):
    employee_ids: List[int]


class ChangeEmployeeCodeRequest(BaseModel):
    new_employee_code: str
    reason: str


class EmployeeCodeHistoryResponse(BaseModel):
    id: int
    employee_id: int
    old_employee_code: Optional[str] = None
    new_employee_code: str
    reason: str
    changed_by: str
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeStatsSummary(BaseModel):
    total: int
    active: int
    on_leave: int
    inactive: int


class EmployeeListResponse(BaseModel):
    data: List[EmployeeResponse]
    total: int
    stats: Optional[EmployeeStatsSummary] = None


class EmployeeCredentialsResponse(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    username: str
    email: EmailStr
    activation_required: bool = True
    temporary_password_hint: str = "The employee must set a password using the activation email."
    status: str

        
