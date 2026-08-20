from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DocumentType(Base):
    __tablename__ = "document_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    category = Column(String(100), nullable=False, default="General")
    required_default = Column(Boolean, default=True, nullable=False)
    allowed_file_types = Column(String(255), default="pdf,jpg,jpeg,png,doc,docx", nullable=False)
    max_file_size_mb = Column(Integer, default=5, nullable=False)
    multiple_allowed = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class EmployeeDocumentRequirement(Base):
    __tablename__ = "employee_document_requirements"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=False, index=True)
    is_required = Column(Boolean, default=True, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="NOT_UPLOADED", nullable=False, index=True)  # NOT_UPLOADED, UPLOADED, PENDING_REVIEW, VERIFIED, REJECTED, RESUBMISSION_REQUIRED, EXPIRED

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("employee_id", "document_type_id", name="uq_emp_doc_type_requirement"),
    )

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    document_type = relationship("DocumentType", foreign_keys=[document_type_id])
    documents = relationship("EmployeeDocument", back_populates="requirement", cascade="all, delete-orphan")


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("employee_document_requirements.id", ondelete="SET NULL"), nullable=True, index=True)

    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String(100), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="PENDING_REVIEW", nullable=False, index=True)  # PENDING_REVIEW, VERIFIED, REJECTED, RESUBMISSION_REQUIRED, EXPIRED

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    rejected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    expiry_date = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    document_type = relationship("DocumentType", foreign_keys=[document_type_id])
    requirement = relationship("EmployeeDocumentRequirement", back_populates="documents", foreign_keys=[requirement_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_user_id])
    versions = relationship("EmployeeDocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="EmployeeDocumentVersion.version_number.desc()")


class EmployeeDocumentVersion(Base):
    __tablename__ = "employee_document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("employee_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False)

    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    rejected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("EmployeeDocument", back_populates="versions")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_user_id])


class DocumentAuditLog(Base):
    __tablename__ = "document_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("employee_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False)  # DOCUMENT_UPLOADED, DOCUMENT_RESUBMITTED, DOCUMENT_VERIFIED, DOCUMENT_REJECTED, DOCUMENT_REPLACED, DOCUMENT_DOWNLOADED, DOCUMENT_DELETED, REQUIREMENT_ADDED, REQUIREMENT_CHANGED
    performed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    performed_by = relationship("User", foreign_keys=[performed_by_user_id])
