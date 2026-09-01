"""Backfill shift and attendance rules default values

Revision ID: a2b3c4d5e6f7
Revises: 12f0873fcfad
Create Date: 2026-09-01 15:18:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = '12f0873fcfad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill NULL columns in shifts and attendance with appropriate defaults."""
    # Backfill shifts table
    op.execute(
        sa.text(
            """
            UPDATE shifts
            SET 
                allow_early_punch_in = COALESCE(allow_early_punch_in, FALSE),
                early_coming_minutes = COALESCE(early_coming_minutes, 60),
                punch_in_grace_minutes = COALESCE(punch_in_grace_minutes, 10),
                shift_grace_minutes = COALESCE(shift_grace_minutes, 15)
            WHERE 
                allow_early_punch_in IS NULL 
                OR early_coming_minutes IS NULL 
                OR punch_in_grace_minutes IS NULL 
                OR shift_grace_minutes IS NULL
            """
        )
    )

    # Backfill document types & employee requirements if empty
    from sqlalchemy.orm import Session
    from app.services.document_service import seed_default_document_types, ensure_all_employees_have_requirements
    
    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        seed_default_document_types(session)
        ensure_all_employees_have_requirements(session)
    finally:
        session.close()
    op.execute(
        sa.text(
            """
            UPDATE attendance
            SET 
                early_arrival_minutes = COALESCE(early_arrival_minutes, 0),
                late_minutes = COALESCE(late_minutes, 0),
                punch_in_grace_minutes = COALESCE(punch_in_grace_minutes, 0),
                early_punch_window_minutes = COALESCE(early_punch_window_minutes, 0),
                shift_grace_minutes = COALESCE(shift_grace_minutes, 0),
                approved_early_minutes = COALESCE(approved_early_minutes, 0),
                unapproved_early_minutes = COALESCE(unapproved_early_minutes, 0),
                regular_work_minutes = COALESCE(regular_work_minutes, 0),
                approved_extra_minutes = COALESCE(approved_extra_minutes, 0),
                early_approval_status = COALESCE(early_approval_status, 'None')
            WHERE 
                early_arrival_minutes IS NULL
                OR late_minutes IS NULL
                OR punch_in_grace_minutes IS NULL
                OR early_punch_window_minutes IS NULL
                OR shift_grace_minutes IS NULL
                OR approved_early_minutes IS NULL
                OR unapproved_early_minutes IS NULL
                OR regular_work_minutes IS NULL
                OR approved_extra_minutes IS NULL
                OR early_approval_status IS NULL
            """
        )
    )


def downgrade() -> None:
    """No downgrade action needed for data backfill."""
    pass
