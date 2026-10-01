"""Add employee code sequence, history audit table, legacy code, and payslip snapshots.

Revision ID: e1f2a3b4c5d6
Revises: fd3e4f5a6b7c
Create Date: 2026-09-29
"""
from typing import Sequence, Union
import re
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "fd3e4f5a6b7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add legacy_employee_code to employees table if not present
    inspector = sa.inspect(conn)
    emp_columns = [c["name"] for c in inspector.get_columns("employees")]
    if "legacy_employee_code" not in emp_columns:
        op.add_column("employees", sa.Column("legacy_employee_code", sa.String(length=50), nullable=True))
        op.create_index(op.f("ix_employees_legacy_employee_code"), "employees", ["legacy_employee_code"], unique=False)

    # 2. Create employee_code_sequences table if not present
    tables = inspector.get_table_names()
    if "employee_code_sequences" not in tables:
        op.create_table(
            "employee_code_sequences",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("prefix", sa.String(length=20), nullable=False, unique=True, index=True),
            sa.Column("next_number", sa.Integer(), nullable=False, default=1),
            sa.Column("padding", sa.Integer(), nullable=False, default=3),
            sa.Column("active", sa.Boolean(), nullable=False, default=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # 3. Create employee_code_history table if not present
    if "employee_code_history" not in tables:
        op.create_table(
            "employee_code_history",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("old_employee_code", sa.String(length=50), nullable=True),
            sa.Column("new_employee_code", sa.String(length=50), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("changed_by", sa.String(length=150), nullable=False),
            sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 4. Add snapshot columns to payslips if not present
    payslip_columns = [c["name"] for c in inspector.get_columns("payslips")]
    if "employee_code_at_generation" not in payslip_columns:
        op.add_column("payslips", sa.Column("employee_code_at_generation", sa.String(length=50), nullable=True))
    if "employee_name_at_generation" not in payslip_columns:
        op.add_column("payslips", sa.Column("employee_name_at_generation", sa.String(length=200), nullable=True))
    if "payroll_year" not in payslip_columns:
        op.add_column("payslips", sa.Column("payroll_year", sa.Integer(), nullable=True))

    # 5. Data Migration: Inspect existing employees to determine highest valid AIVAN number
    employees_tbl = table(
        "employees",
        column("id", sa.Integer),
        column("employee_code", sa.String),
        column("first_name", sa.String),
        column("last_name", sa.String),
    )
    seq_tbl = table(
        "employee_code_sequences",
        column("id", sa.Integer),
        column("prefix", sa.String),
        column("next_number", sa.Integer),
        column("padding", sa.Integer),
        column("active", sa.Boolean),
    )
    history_tbl = table(
        "employee_code_history",
        column("employee_id", sa.Integer),
        column("old_employee_code", sa.String),
        column("new_employee_code", sa.String),
        column("reason", sa.Text),
        column("changed_by", sa.String),
    )

    # Query all employees
    existing_rows = conn.execute(select(employees_tbl.c.id, employees_tbl.c.employee_code, employees_tbl.c.first_name, employees_tbl.c.last_name)).fetchall()
    
    aivan_pattern = re.compile(r"^AIVAN(\d+)$", re.IGNORECASE)
    highest_aivan = 0
    for row in existing_rows:
        code = (row.employee_code or "").strip()
        m = aivan_pattern.match(code)
        if m:
            num = int(m.group(1))
            if num > highest_aivan:
                highest_aivan = num

    # Determine initial next_number for AIVAN
    next_num = (highest_aivan + 1) if highest_aivan > 0 else 1

    # Check if AIVAN sequence already exists
    existing_seq = conn.execute(select(seq_tbl.c.id).where(seq_tbl.c.prefix == "AIVAN")).first()
    if not existing_seq:
        conn.execute(
            seq_tbl.insert().values(
                prefix="AIVAN",
                next_number=next_num,
                padding=3,
                active=True,
            )
        )

    # Seed initial audit history for existing employees if not recorded yet
    existing_history_emp_ids = {h[0] for h in conn.execute(select(history_tbl.c.employee_id)).fetchall()}
    for row in existing_rows:
        if row.id not in existing_history_emp_ids and row.employee_code:
            conn.execute(
                history_tbl.insert().values(
                    employee_id=row.id,
                    old_employee_code=None,
                    new_employee_code=row.employee_code,
                    reason="Initial identity baseline / migration preservation",
                    changed_by="SYSTEM",
                )
            )

    # Backfill existing payslips with snapshots if any exist
    try:
        conn.execute(
            sa.text("""
                UPDATE payslips p
                SET 
                    employee_code_at_generation = e.employee_code,
                    employee_name_at_generation = TRIM(CONCAT(COALESCE(e.first_name, ''), ' ', COALESCE(e.last_name, '')))
                FROM employees e
                WHERE p.employee_id = e.id AND p.employee_code_at_generation IS NULL
            """)
        )
    except Exception:
        # SQLite or other engine compatibility fallback
        pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "employee_code_history" in tables:
        op.drop_table("employee_code_history")
    if "employee_code_sequences" in tables:
        op.drop_table("employee_code_sequences")
