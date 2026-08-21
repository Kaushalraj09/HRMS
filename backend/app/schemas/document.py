from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime, date


# Document Type Schemas
class DocumentTypeBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    category: str = "General"
    required_default: bool = True
    allowed_file_types: str = "pdf,jpg,jpeg,png,doc,docx"
    max_file_size_mb: int = 5
    multiple_allowed: bool = False
    is_active: bool = True


class DocumentTypeCreate(DocumentTypeBase):
    pass


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    required_default: Optional[bool] = None
    allowed_file_types: Optional[str] = None
    max_file_size_mb: Optional[int] = None
    multiple_allowed: Optional[bool] = None
    is_active: Optional[bool] = None


class DocumentTypeResponse(DocumentTypeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Document Version Schema
class DocumentVersionResponse(BaseModel):
    id: int
    document_id: Optional[int] = None
    version_id: Optional[int] = None
    is_current: Optional[bool] = False
    version_number: int
    file_name: str
    file_size: int
    mime_type: str
    status: str
    uploaded_by_name: Optional[str] = None
    uploaded_at: datetime
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejected_by_name: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



# Employee Document Schema
class EmployeeDocumentResponse(BaseModel):
    id: int
    employee_id: int
    document_type_id: int
    document_type_name: str
    document_type_code: str
    category: str
    is_required: bool
    file_name: str
    file_size: int
    mime_type: str
    version: int
    status: str  # PENDING_REVIEW, VERIFIED, REJECTED, RESUBMISSION_REQUIRED, EXPIRED
    uploaded_by_user_id: int
    uploaded_by_name: str
    uploaded_by_role: str
    uploaded_at: datetime
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejected_by_name: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    expiry_date: Optional[date] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Employee Document Requirement with current Document (if any)
class EmployeeDocumentItem(BaseModel):
    requirement_id: Optional[int] = None
    document_type_id: int
    document_type_name: str
    document_type_code: str
    category: str
    description: Optional[str] = None
    is_required: bool
    allowed_file_types: str
    max_file_size_mb: int
    status: str  # NOT_UPLOADED, UPLOADED, PENDING_REVIEW, VERIFIED, REJECTED, RESUBMISSION_REQUIRED, EXPIRED
    due_date: Optional[date] = None
    
    # Active document info (if uploaded)
    document_id: Optional[int] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    version: Optional[int] = None
    uploaded_by_name: Optional[str] = None
    uploaded_by_role: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejected_by_name: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None
    versions_count: int = 0


# Summary & Completion Stats
class DocumentSummaryStats(BaseModel):
    total_required: int = 0
    total_optional: int = 0
    uploaded: int = 0
    pending_review: int = 0
    verified: int = 0
    rejected: int = 0
    missing: int = 0
    completion_percentage: float = 0.0


class EmployeeDocumentsPageResponse(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: str
    department: Optional[str] = None
    designation: Optional[str] = None
    summary: DocumentSummaryStats
    documents: List[EmployeeDocumentItem]


# Review / Verification Request Schemas
class VerifyDocumentRequest(BaseModel):
    remarks: Optional[str] = None


class RejectDocumentRequest(BaseModel):
    reason: str
    remarks: Optional[str] = None


class UpdateRequirementRequest(BaseModel):
    document_type_id: int
    is_required: bool
    due_date: Optional[date] = None


# HR Organization Document KPI Overview
class HrDocumentOverviewKPI(BaseModel):
    total_employees: int = 0
    documents_pending: int = 0
    documents_verified: int = 0
    documents_rejected: int = 0
    incomplete_employees: int = 0
    partial_employees: int = 0
    complete_employees: int = 0
    attention_employees: int = 0
    total_required_docs: int = 8
    overall_compliance_rate: float = 0.0
    categories_breakdown: List[dict] = []


# Audit Log Schema
class DocumentAuditLogResponse(BaseModel):
    id: int
    employee_id: int
    document_id: Optional[int] = None
    action: str
    performed_by_name: str
    performed_by_role: str
    details: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
