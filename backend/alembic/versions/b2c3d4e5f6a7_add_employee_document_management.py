"""add_employee_document_management

Revision ID: b2c3d4e5f6a7
Revises: a1f2e3d4c5b6
Create Date: 2026-08-19 16:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1f2e3d4c5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. document_types
    op.create_table(
        'document_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='General'),
        sa.Column('required_default', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('allowed_file_types', sa.String(length=255), nullable=False, server_default='pdf,jpg,jpeg,png,doc,docx'),
        sa.Column('max_file_size_mb', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('multiple_allowed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_document_types_id'), 'document_types', ['id'], unique=False)
    op.create_index(op.f('ix_document_types_code'), 'document_types', ['code'], unique=True)

    # 2. employee_document_requirements
    op.create_table(
        'employee_document_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('document_type_id', sa.Integer(), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOT_UPLOADED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_type_id'], ['document_types.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'document_type_id', name='uq_emp_doc_type_requirement')
    )
    op.create_index(op.f('ix_employee_document_requirements_id'), 'employee_document_requirements', ['id'], unique=False)
    op.create_index(op.f('ix_employee_document_requirements_employee_id'), 'employee_document_requirements', ['employee_id'], unique=False)
    op.create_index(op.f('ix_employee_document_requirements_document_type_id'), 'employee_document_requirements', ['document_type_id'], unique=False)
    op.create_index(op.f('ix_employee_document_requirements_status'), 'employee_document_requirements', ['status'], unique=False)

    # 3. employee_documents
    op.create_table(
        'employee_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('document_type_id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.Integer(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('verified_by_user_id', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by_user_id', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_type_id'], ['document_types.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requirement_id'], ['employee_document_requirements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_documents_id'), 'employee_documents', ['id'], unique=False)
    op.create_index(op.f('ix_employee_documents_employee_id'), 'employee_documents', ['employee_id'], unique=False)
    op.create_index(op.f('ix_employee_documents_document_type_id'), 'employee_documents', ['document_type_id'], unique=False)
    op.create_index(op.f('ix_employee_documents_requirement_id'), 'employee_documents', ['requirement_id'], unique=False)
    op.create_index(op.f('ix_employee_documents_status'), 'employee_documents', ['status'], unique=False)

    # 4. employee_document_versions
    op.create_table(
        'employee_document_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_by_user_id', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by_user_id', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['employee_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_document_versions_id'), 'employee_document_versions', ['id'], unique=False)
    op.create_index(op.f('ix_employee_document_versions_document_id'), 'employee_document_versions', ['document_id'], unique=False)

    # 5. document_audit_logs
    op.create_table(
        'document_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('performed_by_user_id', sa.Integer(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['employee_documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_audit_logs_id'), 'document_audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_document_audit_logs_employee_id'), 'document_audit_logs', ['employee_id'], unique=False)
    op.create_index(op.f('ix_document_audit_logs_document_id'), 'document_audit_logs', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_table('document_audit_logs')
    op.drop_table('employee_document_versions')
    op.drop_table('employee_documents')
    op.drop_table('employee_document_requirements')
    op.drop_table('document_types')
