import os
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.models.document import DocumentType, EmployeeDocument, EmployeeDocumentRequirement, DocumentAuditLog
from app.core.enums import UserRole

logger = logging.getLogger(__name__)

from app.schemas.document import (
    DocumentTypeCreate,
    DocumentTypeUpdate,
    DocumentTypeResponse,
    EmployeeDocumentsPageResponse,
    EmployeeDocumentResponse,
    DocumentVersionResponse,
    VerifyDocumentRequest,
    RejectDocumentRequest,
    UpdateRequirementRequest,
    HrDocumentOverviewKPI
)
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["document-management"])


def _require_admin_or_hr(current_user: User):
    role = (current_user.role.name if current_user.role else "").lower()
    if role not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and HR personnel are authorized to perform this action"
        )


def _require_admin(current_user: User):
    role = (current_user.role.name if current_user.role else "").lower()
    if role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators are authorized to perform this action"
        )


# ─── Document Types ──────────────────────────────────────────────────────────

@router.get("/types", response_model=List[DocumentTypeResponse])
def get_document_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List document types configured in the system."""
    query = db.query(DocumentType)
    if not include_inactive:
        query = query.filter(DocumentType.is_active == True)
    return query.order_by(DocumentType.id.asc()).all()


@router.post("/types", response_model=DocumentTypeResponse)
def create_document_type(
    payload: DocumentTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new document type (Admin only)."""
    _require_admin(current_user)

    existing = db.query(DocumentType).filter(
        (DocumentType.name == payload.name) | (DocumentType.code == payload.code)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Document type with this name or code already exists")

    doc_type = DocumentType(**payload.model_dump())
    db.add(doc_type)
    db.commit()
    db.refresh(doc_type)

    # Initialize requirement for all existing employees if required by default
    document_service.ensure_all_employees_have_requirements(db)

    return doc_type


@router.put("/types/{type_id}", response_model=DocumentTypeResponse)
def update_document_type(
    type_id: int,
    payload: DocumentTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing document type (Admin only)."""
    _require_admin(current_user)

    doc_type = db.query(DocumentType).filter(DocumentType.id == type_id).first()
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(doc_type, field, val)

    db.commit()
    db.refresh(doc_type)
    return doc_type


@router.delete("/types/{type_id}")
def delete_document_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a document type (Admin only)."""
    _require_admin(current_user)

    doc_type = db.query(DocumentType).filter(DocumentType.id == type_id).first()
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")

    doc_type.is_active = False
    db.commit()
    return {"success": True, "message": f"Document type '{doc_type.name}' has been deactivated"}


# ─── Employee Endpoints ──────────────────────────────────────────────────────

@router.get("/my-documents", response_model=EmployeeDocumentsPageResponse)
def get_my_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current authenticated employee's documents, requirements and summary."""
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        # If user is admin/hr with no employee profile, create or fetch a mock/demo context or return empty
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No employee profile linked to current user account"
        )

    return document_service.get_employee_documents_data(db, emp.id)


@router.post("/upload")
async def upload_my_document(
    document_type_id: int = Form(...),
    file: UploadFile = File(...),
    remarks: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload or resubmit a document for current authenticated employee."""
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="No employee profile linked to current user account")

    doc = await document_service.upload_employee_document(
        db=db,
        employee_id=emp.id,
        document_type_id=document_type_id,
        file=file,
        current_user=current_user,
        remarks=remarks
    )

    return {
        "success": True,
        "message": "Document uploaded successfully. Status: Pending Review",
        "document_id": doc.id,
        "version": doc.version,
        "status": doc.status
    }


# ─── File Download & Preview ─────────────────────────────────────────────────

@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a document with proper ownership authorization check."""
    file_path, file_name, mime_type = document_service.get_document_file_for_user(db, doc_id, current_user)
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'}
    )


@router.get("/{doc_id}/preview")
def preview_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stream a document inline for browser preview (PDF/Image)."""
    file_path, file_name, mime_type = document_service.get_document_file_for_user(db, doc_id, current_user)
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{file_name}"'}
    )


@router.get("/versions/{version_id}/download")
def download_document_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download an archived document version."""
    file_path, file_name, mime_type = document_service.get_version_file_for_user(db, version_id, current_user)
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'}
    )


@router.get("/{doc_id}/history", response_model=List[DocumentVersionResponse])
def get_document_history(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get version history and review remarks for a document."""
    return document_service.get_document_version_history(db, doc_id, current_user)


# ─── HR & Admin Endpoints ────────────────────────────────────────────────────

@router.get("/hr/overview", response_model=HrDocumentOverviewKPI)
def get_hr_document_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get organization-wide document compliance KPIs (HR / Admin only)."""
    _require_admin_or_hr(current_user)
    return document_service.get_hr_documents_kpi_overview(db)


@router.get("/hr/pending")
def get_hr_pending_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str = "",
    department: str = "",
    status_filter: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get documents in review queue for HR verification."""
    _require_admin_or_hr(current_user)
    return document_service.get_hr_pending_reviews(
        db=db,
        page=page,
        limit=limit,
        search=search,
        department=department,
        status_filter=status_filter
    )


@router.get("/hr/employees/{employee_id}", response_model=EmployeeDocumentsPageResponse)
def get_employee_documents_for_hr(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific employee's document requirements and uploads (HR / Admin only)."""
    _require_admin_or_hr(current_user)
    return document_service.get_employee_documents_data(db, employee_id)


@router.post("/hr/employees/{employee_id}/upload")
async def hr_upload_document_for_employee(
    employee_id: int,
    document_type_id: int = Form(...),
    file: UploadFile = File(...),
    remarks: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """HR uploads a document on behalf of an employee."""
    _require_admin_or_hr(current_user)

    doc = await document_service.upload_employee_document(
        db=db,
        employee_id=employee_id,
        document_type_id=document_type_id,
        file=file,
        current_user=current_user,
        remarks=remarks
    )

    return {
        "success": True,
        "message": "Document uploaded successfully on behalf of employee.",
        "document_id": doc.id,
        "version": doc.version,
        "status": doc.status
    }


@router.post("/hr/employees/{employee_id}/requirements")
def update_employee_requirement(
    employee_id: int,
    payload: UpdateRequirementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """HR updates whether a document is required or optional for an employee."""
    _require_admin_or_hr(current_user)

    req = db.query(EmployeeDocumentRequirement).filter(
        EmployeeDocumentRequirement.employee_id == employee_id,
        EmployeeDocumentRequirement.document_type_id == payload.document_type_id
    ).first()

    if not req:
        req = EmployeeDocumentRequirement(
            employee_id=employee_id,
            document_type_id=payload.document_type_id,
            is_required=payload.is_required,
            due_date=payload.due_date,
            status="NOT_UPLOADED"
        )
        db.add(req)
    else:
        req.is_required = payload.is_required
        if payload.due_date is not None:
            req.due_date = payload.due_date

    db.commit()
    return {"success": True, "message": "Employee document requirement updated"}


@router.post("/hr/{doc_id}/verify")
def verify_employee_document(
    doc_id: int,
    payload: Optional[VerifyDocumentRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify an employee document (HR / Admin only)."""
    _require_admin_or_hr(current_user)
    remarks = payload.remarks if payload else None
    doc = document_service.verify_document(db, doc_id, current_user, remarks=remarks)
    return {
        "success": True,
        "message": "Document verified successfully",
        "document_id": doc.id,
        "status": doc.status,
        "verified_at": doc.verified_at
    }


@router.post("/hr/{doc_id}/reject")
def reject_employee_document(
    doc_id: int,
    payload: RejectDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject an employee document with mandatory reason (HR / Admin only)."""
    _require_admin_or_hr(current_user)
    doc = document_service.reject_document(
        db,
        doc_id=doc_id,
        reason=payload.reason,
        current_user=current_user,
        remarks=payload.remarks
    )
    return {
        "success": True,
        "message": "Document rejected. Re-upload request sent to employee.",
        "document_id": doc.id,
        "status": doc.status,
        "rejection_reason": doc.rejection_reason
    }


@router.delete("/hr/{doc_id}")
def delete_employee_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an unverified/rejected document (HR / Admin only)."""
    _require_admin_or_hr(current_user)

    doc = db.query(EmployeeDocument).filter(EmployeeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status in ["VERIFIED", "APPROVED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verified documents cannot be deleted directly. Mark as unverified or rejected prior to deletion."
        )

    employee_id = doc.employee_id
    document_type_id = doc.document_type_id
    file_name = doc.file_name

    # Remove the current file and every archived version before changing the
    # database.  If storage cannot be updated, keep the DB record intact so
    # the document is not orphaned and the operation can be retried safely.
    file_paths = {doc.storage_path}
    file_paths.update(version.storage_path for version in doc.versions)
    try:
        for file_path in filter(None, file_paths):
            if os.path.exists(file_path):
                os.remove(file_path)
    except OSError as exc:
        logger.exception("Failed to remove document file during deletion", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document file could not be deleted; no database changes were made.",
        ) from exc

    # This must be committed atomically with the record deletion.  `details`
    # is the model's structured audit field (there is no `notes` column).
    db.add(DocumentAuditLog(
        document_id=doc.id,
        employee_id=employee_id,
        action="DOCUMENT_DELETED",
        performed_by_user_id=current_user.id,
        details={"file_name": file_name, "deleted_by_user_id": current_user.id},
    ))

    # Revert requirement status
    req = db.query(EmployeeDocumentRequirement).filter(
        EmployeeDocumentRequirement.employee_id == employee_id,
        EmployeeDocumentRequirement.document_type_id == document_type_id
    ).first()
    if req:
        req.status = "NOT_UPLOADED"

    db.delete(doc)
    db.commit()

    return {"success": True, "message": "Document deleted successfully"}
