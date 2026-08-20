import os
import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date, timezone
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.models.document import (
    DocumentType,
    EmployeeDocumentRequirement,
    EmployeeDocument,
    EmployeeDocumentVersion,
    DocumentAuditLog
)
from app.models.employee import Employee
from app.models.user import User, Role
from app.core.enums import UserRole
from app.schemas.document import (
    DocumentSummaryStats,
    EmployeeDocumentItem,
    EmployeeDocumentsPageResponse,
    DocumentVersionResponse,
    DocumentAuditLogResponse,
    HrDocumentOverviewKPI
)

logger = logging.getLogger(__name__)

# Base private storage directory for documents
STORAGE_BASE_DIR = Path(__file__).resolve().parents[2] / "storage" / "documents"


def _ensure_storage_dir(employee_id: int) -> Path:
    target_dir = STORAGE_BASE_DIR / str(employee_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _run_async_notification(coro):
    """Run an async notification safely from synchronous context."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, loop)
    else:
        loop.run_until_complete(coro)


# ─── 1. Seeding & Master Data ────────────────────────────────────────────────

DEFAULT_DOCUMENT_TYPES = [
    {
        "name": "Aadhaar Card",
        "code": "AADHAAR",
        "category": "Identity Proof",
        "description": "Government issued Aadhaar card (front and back).",
        "required_default": True,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "PAN Card",
        "code": "PAN",
        "category": "Identity Proof",
        "description": "Permanent Account Number (PAN) card copy.",
        "required_default": True,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "Passport Size Photograph",
        "code": "PHOTO",
        "category": "Identity Proof",
        "description": "Recent passport size photograph with clear background.",
        "required_default": True,
        "allowed_file_types": "jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "Bank Passbook / Cancelled Cheque",
        "code": "BANK_PROOF",
        "category": "Financial",
        "description": "Cancelled cheque or first page of bank passbook showing account number and IFSC.",
        "required_default": True,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "Address Proof",
        "code": "ADDRESS_PROOF",
        "category": "Identity Proof",
        "description": "Electricity bill, voter ID, rent agreement, or passport.",
        "required_default": True,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "10th Marksheet (SSC)",
        "code": "10TH_MARKSHEET",
        "category": "Academic & Professional",
        "description": "10th standard (SSC / Matriculation) marksheet or board passing certificate.",
        "required_default": True,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 10,
        "multiple_allowed": False
    },
    {
        "name": "12th Marksheet (HSC) / Diploma Marksheet",
        "code": "12TH_OR_DIPLOMA_MARKSHEET",
        "category": "Academic & Professional",
        "description": "12th standard (HSC / Intermediate) marksheet OR Diploma final marksheet / passing certificate.",
        "required_default": True,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 10,
        "multiple_allowed": False
    },
    {
        "name": "Graduation / Degree Certificate",
        "code": "DEGREE_CERT",
        "category": "Academic & Professional",
        "description": "Bachelor's / Master's degree passing certificate or consolidated marksheet.",
        "required_default": True,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": True
    },
    {
        "name": "Diploma Certificate",
        "code": "DIPLOMA_CERT",
        "category": "Academic & Professional",
        "description": "Polytechnic or technical diploma certificate / semester marksheets (if applicable).",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": False
    },
    {
        "name": "Educational Certificate (Other)",
        "code": "EDUCATION_CERT",
        "category": "Academic & Professional",
        "description": "Additional degree, diploma, post-graduate, or certification passing documents.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": True
    },
    {
        "name": "Experience Letter",
        "code": "EXPERIENCE_LETTER",
        "category": "Academic & Professional",
        "description": "Experience or service certificate from previous organization(s).",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": True
    },
    {
        "name": "Relieving Letter",
        "code": "RELIEVING_LETTER",
        "category": "Academic & Professional",
        "description": "Relieving letter or formal exit confirmation from last employer.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": False
    },
    {
        "name": "Offer Letter",
        "code": "OFFER_LETTER",
        "category": "Onboarding",
        "description": "Signed employment offer letter.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": False
    },
    {
        "name": "Joining Letter",
        "code": "JOINING_LETTER",
        "category": "Onboarding",
        "description": "Formal joining letter or appointment letter copy.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": False
    },
    {
        "name": "Passport",
        "code": "PASSPORT",
        "category": "Identity Proof",
        "description": "Valid passport first and last pages.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "Driving License",
        "code": "DRIVING_LICENSE",
        "category": "Identity Proof",
        "description": "Valid driving license copy.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "Salary Certificate / Pay Slips",
        "code": "SALARY_CERT",
        "category": "Financial",
        "description": "Last 3 months salary slips from previous employer.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 10,
        "multiple_allowed": True
    },
    {
        "name": "Medical Certificate",
        "code": "MEDICAL_CERT",
        "category": "Medical",
        "description": "Fitness / medical checkup certificate.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png",
        "max_file_size_mb": 5,
        "multiple_allowed": False
    },
    {
        "name": "Other Document",
        "code": "OTHER",
        "category": "Other",
        "description": "Any additional supporting or compliance document.",
        "required_default": False,
        "allowed_file_types": "pdf,jpg,jpeg,png,doc,docx",
        "max_file_size_mb": 10,
        "multiple_allowed": True
    }
]


def seed_default_document_types(db: Session) -> None:
    """Seed standard document types into document_types table if missing, or update metadata."""
    for dt_data in DEFAULT_DOCUMENT_TYPES:
        existing = db.query(DocumentType).filter(
            or_(DocumentType.code == dt_data["code"], DocumentType.name == dt_data["name"])
        ).first()
        if not existing:
            doc_type = DocumentType(**dt_data, is_active=True)
            db.add(doc_type)
            print(f"Added document type: {dt_data['name']}")
        else:
            existing.description = dt_data["description"]
            existing.allowed_file_types = dt_data["allowed_file_types"]
            existing.max_file_size_mb = dt_data["max_file_size_mb"]
            existing.category = dt_data["category"]
            existing.is_active = True
    db.commit()


def get_active_document_types(db: Session) -> List[DocumentType]:
    return db.query(DocumentType).filter(DocumentType.is_active == True).order_by(DocumentType.id.asc()).all()


# ─── 2. Requirement Initialization ──────────────────────────────────────────

def initialize_employee_requirements(db: Session, employee_id: int) -> None:
    """Safely initialize default document requirements for an employee."""
    active_types = get_active_document_types(db)
    for dt in active_types:
        req = db.query(EmployeeDocumentRequirement).filter(
            EmployeeDocumentRequirement.employee_id == employee_id,
            EmployeeDocumentRequirement.document_type_id == dt.id
        ).first()
        if not req:
            req = EmployeeDocumentRequirement(
                employee_id=employee_id,
                document_type_id=dt.id,
                is_required=dt.required_default,
                status="NOT_UPLOADED"
            )
            db.add(req)
    db.commit()


def ensure_all_employees_have_requirements(db: Session) -> None:
    """Backfill missing requirements for any existing employees."""
    employees = db.query(Employee).filter(Employee.status != "Deleted").all()
    for emp in employees:
        initialize_employee_requirements(db, emp.id)


# ─── 3. Document Summary & Details ───────────────────────────────────────────

def get_employee_documents_data(db: Session, employee_id: int) -> EmployeeDocumentsPageResponse:
    """Fetch complete document requirements, uploaded documents, versions count, and stats."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Ensure requirements exist
    initialize_employee_requirements(db, employee_id)

    # Fetch all requirements joining document_type
    requirements = (
        db.query(EmployeeDocumentRequirement)
        .options(joinedload(EmployeeDocumentRequirement.document_type))
        .filter(EmployeeDocumentRequirement.employee_id == employee_id)
        .all()
    )

    items: List[EmployeeDocumentItem] = []
    total_required = 0
    total_optional = 0
    uploaded_count = 0
    pending_count = 0
    verified_count = 0
    rejected_count = 0
    missing_count = 0

    for req in requirements:
        dt = req.document_type
        if not dt or not dt.is_active:
            continue

        if req.is_required:
            total_required += 1
        else:
            total_optional += 1

        # Fetch latest active document for this employee and doc_type
        doc = (
            db.query(EmployeeDocument)
            .options(
                joinedload(EmployeeDocument.uploaded_by),
                joinedload(EmployeeDocument.verified_by),
                joinedload(EmployeeDocument.rejected_by),
            )
            .filter(
                EmployeeDocument.employee_id == employee_id,
                EmployeeDocument.document_type_id == dt.id
            )
            .order_by(EmployeeDocument.id.desc())
            .first()
        )

        effective_status = req.status
        doc_id = None
        file_name = None
        file_size = None
        mime_type = None
        version = None
        uploaded_by_name = None
        uploaded_by_role = None
        uploaded_at = None
        verified_by_name = None
        verified_at = None
        rejected_by_name = None
        rejected_at = None
        rejection_reason = None
        remarks = None
        versions_count = 0

        if doc:
            doc_id = doc.id
            file_name = doc.file_name
            file_size = doc.file_size
            mime_type = doc.mime_type
            version = doc.version
            uploaded_by_name = doc.uploaded_by.display_name if doc.uploaded_by else "System"
            uploaded_by_role = doc.uploaded_by.role.name if (doc.uploaded_by and doc.uploaded_by.role) else "User"
            uploaded_at = doc.uploaded_at
            verified_by_name = doc.verified_by.display_name if doc.verified_by else None
            verified_at = doc.verified_at
            rejected_by_name = doc.rejected_by.display_name if doc.rejected_by else None
            rejected_at = doc.rejected_at
            rejection_reason = doc.rejection_reason
            remarks = doc.remarks
            effective_status = doc.status

            # Count versions
            versions_count = db.query(EmployeeDocumentVersion).filter(
                EmployeeDocumentVersion.document_id == doc.id
            ).count() + 1

            uploaded_count += 1
            if doc.status == "VERIFIED":
                verified_count += 1
            elif doc.status == "PENDING_REVIEW":
                pending_count += 1
            elif doc.status in ["REJECTED", "RESUBMISSION_REQUIRED"]:
                rejected_count += 1
        else:
            effective_status = "NOT_UPLOADED"
            if req.is_required:
                missing_count += 1

        items.append(EmployeeDocumentItem(
            requirement_id=req.id,
            document_type_id=dt.id,
            document_type_name=dt.name,
            document_type_code=dt.code,
            category=dt.category,
            description=dt.description,
            is_required=req.is_required,
            allowed_file_types=dt.allowed_file_types,
            max_file_size_mb=dt.max_file_size_mb,
            status=effective_status,
            due_date=req.due_date,
            document_id=doc_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            version=version,
            uploaded_by_name=uploaded_by_name,
            uploaded_by_role=uploaded_by_role,
            uploaded_at=uploaded_at,
            verified_by_name=verified_by_name,
            verified_at=verified_at,
            rejected_by_name=rejected_by_name,
            rejected_at=rejected_at,
            rejection_reason=rejection_reason,
            remarks=remarks,
            versions_count=versions_count
        ))

    # Calculate completion percentage: verified_required / total_required * 100
    verified_required = sum(1 for item in items if item.is_required and item.status == "VERIFIED")
    completion_percentage = (
        round((verified_required / total_required) * 100, 1) if total_required > 0 else 100.0
    )

    summary = DocumentSummaryStats(
        total_required=total_required,
        total_optional=total_optional,
        uploaded=uploaded_count,
        pending_review=pending_count,
        verified=verified_count,
        rejected=rejected_count,
        missing=missing_count,
        completion_percentage=completion_percentage
    )

    return EmployeeDocumentsPageResponse(
        employee_id=employee.id,
        employee_name=f"{employee.first_name} {employee.last_name}".strip(),
        employee_code=employee.employee_code,
        department=employee.department,
        designation=employee.designation,
        summary=summary,
        documents=items
    )


# ─── 4. File Upload, Validation & Versioning ─────────────────────────────────

async def upload_employee_document(
    db: Session,
    employee_id: int,
    document_type_id: int,
    file: UploadFile,
    current_user: User,
    remarks: Optional[str] = None
) -> EmployeeDocument:
    """Handle document upload / resubmission with strict validation and version archiving."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    doc_type = db.query(DocumentType).filter(DocumentType.id == document_type_id).first()
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")

    if not doc_type.is_active:
        raise HTTPException(status_code=400, detail="This document type is inactive")

    # 1. Validate file extension
    file_name = file.filename or "uploaded_file"
    file_ext = file_name.split(".")[-1].lower() if "." in file_name else ""
    allowed_exts = [ext.strip().lower() for ext in doc_type.allowed_file_types.split(",") if ext.strip()]

    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '.{file_ext}'. Allowed extensions: {', '.join(allowed_exts)}"
        )

    # 2. Read content & validate file size
    contents = await file.read()
    file_size = len(contents)
    max_size_bytes = doc_type.max_file_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {doc_type.max_file_size_mb} MB"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    mime_type = file.content_type or "application/octet-stream"

    # 3. Store file safely in private storage directory
    target_dir = _ensure_storage_dir(employee_id)
    unique_file_name = f"{doc_type.code.lower()}_{uuid.uuid4().hex[:12]}.{file_ext}"
    saved_file_path = target_dir / unique_file_name

    with open(saved_file_path, "wb") as f:
        f.write(contents)

    # 4. Find or create requirement
    req = db.query(EmployeeDocumentRequirement).filter(
        EmployeeDocumentRequirement.employee_id == employee_id,
        EmployeeDocumentRequirement.document_type_id == document_type_id
    ).first()

    if not req:
        req = EmployeeDocumentRequirement(
            employee_id=employee_id,
            document_type_id=document_type_id,
            is_required=doc_type.required_default,
            status="PENDING_REVIEW"
        )
        db.add(req)
        db.flush()

    # 5. Check for existing active document
    existing_doc = db.query(EmployeeDocument).filter(
        EmployeeDocument.employee_id == employee_id,
        EmployeeDocument.document_type_id == document_type_id
    ).first()

    action = "DOCUMENT_UPLOADED"

    if existing_doc:
        action = "DOCUMENT_RESUBMITTED"
        # Archive current document version to EmployeeDocumentVersion
        version_archive = EmployeeDocumentVersion(
            document_id=existing_doc.id,
            version_number=existing_doc.version,
            file_name=existing_doc.file_name,
            storage_path=existing_doc.storage_path,
            file_size=existing_doc.file_size,
            mime_type=existing_doc.mime_type,
            status=existing_doc.status,
            uploaded_by_user_id=existing_doc.uploaded_by_user_id,
            uploaded_at=existing_doc.uploaded_at,
            verified_by_user_id=existing_doc.verified_by_user_id,
            verified_at=existing_doc.verified_at,
            rejected_by_user_id=existing_doc.rejected_by_user_id,
            rejected_at=existing_doc.rejected_at,
            rejection_reason=existing_doc.rejection_reason,
            remarks=existing_doc.remarks
        )
        db.add(version_archive)

        # Update existing document with new version
        existing_doc.version += 1
        existing_doc.file_name = file_name
        existing_doc.storage_path = str(saved_file_path)
        existing_doc.file_size = file_size
        existing_doc.mime_type = mime_type
        existing_doc.status = "PENDING_REVIEW"
        existing_doc.uploaded_by_user_id = current_user.id
        existing_doc.uploaded_at = func.now()
        existing_doc.verified_by_user_id = None
        existing_doc.verified_at = None
        existing_doc.rejected_by_user_id = None
        existing_doc.rejected_at = None
        existing_doc.rejection_reason = None
        existing_doc.remarks = remarks
        document = existing_doc
    else:
        document = EmployeeDocument(
            employee_id=employee_id,
            document_type_id=document_type_id,
            requirement_id=req.id,
            file_name=file_name,
            storage_path=str(saved_file_path),
            file_size=file_size,
            mime_type=mime_type,
            version=1,
            status="PENDING_REVIEW",
            uploaded_by_user_id=current_user.id,
            remarks=remarks
        )
        db.add(document)
        db.flush()

    req.status = "PENDING_REVIEW"

    # 6. Audit log
    audit = DocumentAuditLog(
        employee_id=employee_id,
        document_id=document.id,
        action=action,
        performed_by_user_id=current_user.id,
        details={
            "document_type": doc_type.name,
            "version": document.version,
            "file_name": file_name,
            "file_size": file_size
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(document)

    # 7. Notifications dispatch
    from app.services.notification_service import create_notification, create_notification_for_roles
    is_hr_user = current_user.role and current_user.role.name.lower() in ["admin", "hr"]

    if not is_hr_user:
        # Notify HR team that employee uploaded document for review
        _run_async_notification(create_notification_for_roles(
            db=db,
            roles=["hr", "admin"],
            type="DOCUMENT_UPLOAD",
            title="Document Uploaded for Verification",
            message=f"{employee.first_name} {employee.last_name} uploaded {doc_type.name} for verification.",
            category="DOCUMENT",
            severity="INFO",
            employee_id=employee.id,
            reference_id=document.id
        ))
    else:
        # HR uploaded on behalf of employee -> Notify employee
        if employee.user_id:
            _run_async_notification(create_notification(
                db=db,
                user_id=employee.user_id,
                type="DOCUMENT_UPLOAD",
                title="Document Uploaded by HR",
                message=f"HR ({current_user.display_name}) has uploaded {doc_type.name} on your behalf.",
                category="DOCUMENT",
                severity="INFO",
                employee_id=employee.id,
                reference_id=document.id
            ))

    return document


# ─── 5. Verification & Rejection Workflows ───────────────────────────────────

def verify_document(
    db: Session,
    doc_id: int,
    current_user: User,
    remarks: Optional[str] = None
) -> EmployeeDocument:
    """Verify an employee document (HR / Admin only)."""
    document = (
        db.query(EmployeeDocument)
        .options(
            joinedload(EmployeeDocument.employee),
            joinedload(EmployeeDocument.document_type),
            joinedload(EmployeeDocument.requirement)
        )
        .filter(EmployeeDocument.id == doc_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document.status = "VERIFIED"
    document.verified_by_user_id = current_user.id
    document.verified_at = datetime.now(timezone.utc)
    document.rejected_by_user_id = None
    document.rejected_at = None
    document.rejection_reason = None
    if remarks:
        document.remarks = remarks

    if document.requirement:
        document.requirement.status = "VERIFIED"

    # Audit log
    audit = DocumentAuditLog(
        employee_id=document.employee_id,
        document_id=document.id,
        action="DOCUMENT_VERIFIED",
        performed_by_user_id=current_user.id,
        details={
            "document_type": document.document_type.name if document.document_type else "",
            "version": document.version,
            "remarks": remarks
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(document)

    # Notify employee
    if document.employee and document.employee.user_id:
        from app.services.notification_service import create_notification
        doc_name = document.document_type.name if document.document_type else "Document"
        _run_async_notification(create_notification(
            db=db,
            user_id=document.employee.user_id,
            type="DOCUMENT_VERIFIED",
            title="Document Verified",
            message=f"Your {doc_name} has been verified by {current_user.display_name}.",
            category="DOCUMENT",
            severity="SUCCESS",
            employee_id=document.employee_id,
            reference_id=document.id
        ))

    return document


def reject_document(
    db: Session,
    doc_id: int,
    reason: str,
    current_user: User,
    remarks: Optional[str] = None
) -> EmployeeDocument:
    """Reject an employee document requiring rejection reason (HR / Admin only)."""
    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Rejection reason is mandatory")

    document = (
        db.query(EmployeeDocument)
        .options(
            joinedload(EmployeeDocument.employee),
            joinedload(EmployeeDocument.document_type),
            joinedload(EmployeeDocument.requirement)
        )
        .filter(EmployeeDocument.id == doc_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document.status = "REJECTED"
    document.rejected_by_user_id = current_user.id
    document.rejected_at = datetime.now(timezone.utc)
    document.rejection_reason = reason.strip()
    if remarks:
        document.remarks = remarks

    if document.requirement:
        document.requirement.status = "RESUBMISSION_REQUIRED"

    # Audit log
    audit = DocumentAuditLog(
        employee_id=document.employee_id,
        document_id=document.id,
        action="DOCUMENT_REJECTED",
        performed_by_user_id=current_user.id,
        details={
            "document_type": document.document_type.name if document.document_type else "",
            "version": document.version,
            "reason": reason.strip(),
            "remarks": remarks
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(document)

    # Notify employee
    if document.employee and document.employee.user_id:
        from app.services.notification_service import create_notification
        doc_name = document.document_type.name if document.document_type else "Document"
        _run_async_notification(create_notification(
            db=db,
            user_id=document.employee.user_id,
            type="DOCUMENT_REJECTED",
            title="Document Requires Re-upload",
            message=f"Your {doc_name} was rejected. Reason: {reason.strip()}",
            category="DOCUMENT",
            severity="WARNING",
            employee_id=document.employee_id,
            reference_id=document.id
        ))

    return document


# ─── 6. File Streaming & Security ────────────────────────────────────────────

def get_document_file_for_user(
    db: Session,
    doc_id: int,
    current_user: User
) -> Tuple[str, str, str]:
    """
    Validate authorization and return (file_path, file_name, mime_type) for secure streaming.
    Employees can only download/preview their own documents.
    HR / Admin can access all.
    """
    document = db.query(EmployeeDocument).filter(EmployeeDocument.id == doc_id).first()
    if not document:
        # Check in versions if old version requested
        raise HTTPException(status_code=404, detail="Document not found")

    user_role = (current_user.role.name if current_user.role else "").lower()

    if user_role not in [UserRole.ADMIN, UserRole.HR]:
        # Must be own employee
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp or emp.id != document.employee_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")

    file_path = Path(document.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file does not exist on disk")

    # Record download audit
    audit = DocumentAuditLog(
        employee_id=document.employee_id,
        document_id=document.id,
        action="DOCUMENT_DOWNLOADED",
        performed_by_user_id=current_user.id,
        details={"file_name": document.file_name}
    )
    db.add(audit)
    db.commit()

    return str(file_path), document.file_name, document.mime_type


def get_version_file_for_user(
    db: Session,
    version_id: int,
    current_user: User
) -> Tuple[str, str, str]:
    """Securely download a historical version."""
    version = db.query(EmployeeDocumentVersion).filter(EmployeeDocumentVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found")

    doc = db.query(EmployeeDocument).filter(EmployeeDocument.id == version.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Associated document record not found")

    user_role = (current_user.role.name if current_user.role else "").lower()
    if user_role not in [UserRole.ADMIN, UserRole.HR]:
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp or emp.id != doc.employee_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document version")

    file_path = Path(version.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Version file does not exist on disk")

    return str(file_path), version.file_name, version.mime_type


# ─── 7. Version History & Audit Trail ────────────────────────────────────────

def get_document_version_history(
    db: Session,
    doc_id: int,
    current_user: User
) -> List[DocumentVersionResponse]:
    """Retrieve full version history of a document."""
    document = db.query(EmployeeDocument).filter(EmployeeDocument.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    user_role = (current_user.role.name if current_user.role else "").lower()
    if user_role not in [UserRole.ADMIN, UserRole.HR]:
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp or emp.id != document.employee_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this document history")

    versions = (
        db.query(EmployeeDocumentVersion)
        .options(
            joinedload(EmployeeDocumentVersion.uploaded_by),
            joinedload(EmployeeDocumentVersion.verified_by),
            joinedload(EmployeeDocumentVersion.rejected_by)
        )
        .filter(EmployeeDocumentVersion.document_id == doc_id)
        .order_by(EmployeeDocumentVersion.version_number.desc())
        .all()
    )

    history_list: List[DocumentVersionResponse] = []

    # Current version
    history_list.append(DocumentVersionResponse(
        id=document.id,
        version_number=document.version,
        file_name=document.file_name,
        file_size=document.file_size,
        mime_type=document.mime_type,
        status=document.status,
        uploaded_by_name=document.uploaded_by.display_name if document.uploaded_by else "System",
        uploaded_at=document.uploaded_at,
        verified_by_name=document.verified_by.display_name if document.verified_by else None,
        verified_at=document.verified_at,
        rejected_by_name=document.rejected_by.display_name if document.rejected_by else None,
        rejected_at=document.rejected_at,
        rejection_reason=document.rejection_reason,
        remarks=document.remarks
    ))

    # Older versions
    for v in versions:
        history_list.append(DocumentVersionResponse(
            id=v.id,
            version_number=v.version_number,
            file_name=v.file_name,
            file_size=v.file_size,
            mime_type=v.mime_type,
            status=v.status,
            uploaded_by_name=v.uploaded_by.display_name if v.uploaded_by else "System",
            uploaded_at=v.uploaded_at,
            verified_by_name=v.verified_by.display_name if v.verified_by else None,
            verified_at=v.verified_at,
            rejected_by_name=v.rejected_by.display_name if v.rejected_by else None,
            rejected_at=v.rejected_at,
            rejection_reason=v.rejection_reason,
            remarks=v.remarks
        ))

    return history_list


# ─── 8. HR Organization Compliance KPI Overview ──────────────────────────────

def get_hr_documents_kpi_overview(db: Session) -> HrDocumentOverviewKPI:
    """Compute organization-wide document metrics for HR dashboard."""
    employees = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .filter(Employee.status == "Active", User.status == "Active")
        .all()
    )
    total_employees = len(employees)

    if total_employees == 0:
        return HrDocumentOverviewKPI(
            total_employees=0,
            documents_pending=0,
            documents_verified=0,
            documents_rejected=0,
            incomplete_employees=0,
            partial_employees=0,
            complete_employees=0,
            attention_employees=0,
            total_required_docs=8,
            overall_compliance_rate=0.0,
            categories_breakdown=[]
        )

    # Aggregate document counts
    docs_pending = db.query(EmployeeDocument).filter(EmployeeDocument.status == "PENDING_REVIEW").count()
    docs_verified = db.query(EmployeeDocument).filter(EmployeeDocument.status == "VERIFIED").count()
    docs_rejected = db.query(EmployeeDocument).filter(EmployeeDocument.status.in_(["REJECTED", "RESUBMISSION_REQUIRED"])).count()

    complete_emps = 0
    partial_emps = 0
    incomplete_emps = 0
    total_verified_pct_sum = 0.0
    total_req_docs_count = 8

    for emp in employees:
        data = get_employee_documents_data(db, emp.id)
        pct = data.summary.completion_percentage
        v_count = data.summary.verified
        u_count = data.summary.uploaded
        tot_req = data.summary.total_required or 8
        total_req_docs_count = tot_req

        total_verified_pct_sum += pct
        if pct >= 100.0 or v_count >= tot_req:
            complete_emps += 1
        elif v_count >= 3 or u_count >= 3 or pct > 0:
            partial_emps += 1
        else:
            incomplete_emps += 1

    attention_emps = total_employees - complete_emps
    overall_rate = round(total_verified_pct_sum / total_employees, 1) if total_employees > 0 else 0.0

    return HrDocumentOverviewKPI(
        total_employees=total_employees,
        documents_pending=docs_pending,
        documents_verified=docs_verified,
        documents_rejected=docs_rejected,
        incomplete_employees=incomplete_emps,
        partial_employees=partial_emps,
        complete_employees=complete_emps,
        attention_employees=attention_emps,
        total_required_docs=total_req_docs_count,
        overall_compliance_rate=overall_rate
    )


# ─── 9. HR Pending Documents Review Queue ────────────────────────────────────

def get_hr_pending_reviews(
    db: Session,
    page: int = 1,
    limit: int = 10,
    search: str = "",
    department: str = "",
    status_filter: str = ""
) -> Dict[str, Any]:
    """Retrieve documents in pending or rejected states for HR verification center."""
    query = (
        db.query(EmployeeDocument)
        .join(Employee, EmployeeDocument.employee_id == Employee.id)
        .join(DocumentType, EmployeeDocument.document_type_id == DocumentType.id)
        .options(
            joinedload(EmployeeDocument.employee),
            joinedload(EmployeeDocument.document_type),
            joinedload(EmployeeDocument.uploaded_by),
            joinedload(EmployeeDocument.verified_by),
            joinedload(EmployeeDocument.rejected_by)
        )
        .filter(Employee.status != "Deleted")
    )

    if status_filter:
        query = query.filter(EmployeeDocument.status == status_filter)
    else:
        query = query.filter(EmployeeDocument.status.in_(["PENDING_REVIEW", "REJECTED"]))

    if department:
        query = query.filter(Employee.department == department)

    if search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
                Employee.employee_code.ilike(term),
                DocumentType.name.ilike(term),
                EmployeeDocument.file_name.ilike(term)
            )
        )

    total = query.count()
    items = query.order_by(EmployeeDocument.uploaded_at.desc()).offset((page - 1) * limit).limit(limit).all()

    formatted_items = []
    for d in items:
        formatted_items.append({
            "id": d.id,
            "employee_id": d.employee_id,
            "employee_name": f"{d.employee.first_name} {d.employee.last_name}".strip() if d.employee else "Unknown",
            "employee_code": d.employee.employee_code if d.employee else "",
            "department": d.employee.department if d.employee else "",
            "document_type_id": d.document_type_id,
            "document_type_name": d.document_type.name if d.document_type else "",
            "category": d.document_type.category if d.document_type else "",
            "file_name": d.file_name,
            "file_size": d.file_size,
            "mime_type": d.mime_type,
            "version": d.version,
            "status": d.status,
            "uploaded_by_name": d.uploaded_by.display_name if d.uploaded_by else "Employee",
            "uploaded_by_role": d.uploaded_by.role.name if (d.uploaded_by and d.uploaded_by.role) else "employee",
            "uploaded_at": d.uploaded_at,
            "rejection_reason": d.rejection_reason,
            "remarks": d.remarks
        })

    return {
        "data": formatted_items,
        "total": total,
        "page": page,
        "limit": limit
    }
