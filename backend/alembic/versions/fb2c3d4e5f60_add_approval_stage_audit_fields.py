"""preserve manager-stage approval audit fields

Revision ID: fb2c3d4e5f60
Revises: fa1b2c3d4e5f
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fb2c3d4e5f60"
down_revision: Union[str, Sequence[str], None] = "fa1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("approval_tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("manager_reviewed_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("manager_reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("manager_decision_comment", sa.String(length=500), nullable=True))
        batch_op.create_foreign_key(
            "fk_approval_tasks_manager_reviewed_by",
            "users",
            ["manager_reviewed_by"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("approval_tasks", schema=None) as batch_op:
        batch_op.drop_constraint("fk_approval_tasks_manager_reviewed_by", type_="foreignkey")
        batch_op.drop_column("manager_decision_comment")
        batch_op.drop_column("manager_reviewed_at")
        batch_op.drop_column("manager_reviewed_by")
