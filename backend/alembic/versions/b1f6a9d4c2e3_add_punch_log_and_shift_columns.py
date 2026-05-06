"""Add punch log table and shift tracking columns

Revision ID: b1f6a9d4c2e3
Revises: 8e7d2a6c9f12
Create Date: 2026-05-06 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1f6a9d4c2e3"
down_revision: Union[str, Sequence[str], None] = "8e7d2a6c9f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    attendance_columns = {column["name"] for column in inspector.get_columns("attendance")}
    if "total_worked_seconds" not in attendance_columns:
        op.add_column("attendance", sa.Column("total_worked_seconds", sa.Integer(), nullable=False, server_default="0"))
    if "is_working" not in attendance_columns:
        op.add_column("attendance", sa.Column("is_working", sa.Integer(), nullable=False, server_default="0"))

    existing_tables = set(inspector.get_table_names())
    if "punch_logs" not in existing_tables:
        op.create_table(
            "punch_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("attendance_id", sa.Integer(), nullable=True),
            sa.Column("date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
            sa.Column("punch_in", sa.DateTime(timezone=True), nullable=True),
            sa.Column("punch_out", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("work_mode", sa.String(length=20), nullable=True, server_default="Office"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["attendance_id"], ["attendance.id"]),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    punch_log_indexes = {index["name"] for index in inspector.get_indexes("punch_logs")} if "punch_logs" in set(sa.inspect(bind).get_table_names()) else set()
    if op.f("ix_punch_logs_id") not in punch_log_indexes:
        op.create_index(op.f("ix_punch_logs_id"), "punch_logs", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_punch_logs_id"), table_name="punch_logs")
    op.drop_table("punch_logs")
    op.drop_column("attendance", "is_working")
    op.drop_column("attendance", "total_worked_seconds")
