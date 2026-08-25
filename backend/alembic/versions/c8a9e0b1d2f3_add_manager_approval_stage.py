"""Add reporting manager and two-stage time-off approval.

Revision ID: c8a9e0b1d2f3
Revises: 9c76cbfeaf96
"""
from alembic import op
import sqlalchemy as sa

revision = "c8a9e0b1d2f3"
down_revision = "9c76cbfeaf96"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reporting_manager_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_employees_reporting_manager", "employees", ["reporting_manager_id"], ["id"])
        batch_op.create_index("ix_employees_reporting_manager_id", ["reporting_manager_id"])
    op.add_column("timeoff_requests", sa.Column("approval_stage", sa.String(length=20), nullable=False, server_default="Manager"))


def downgrade():
    op.drop_column("timeoff_requests", "approval_stage")
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_index("ix_employees_reporting_manager_id")
        batch_op.drop_constraint("fk_employees_reporting_manager", type_="foreignkey")
        batch_op.drop_column("reporting_manager_id")
