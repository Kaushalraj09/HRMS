"""add system defined leaves and lop policy

Revision ID: e2f3a4b5c6d7
Revises: e1f2a3b4c5d6
Create Date: 2026-10-01 14:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    lt_columns = [c["name"] for c in inspector.get_columns("leave_types")]

    # Add columns to leave_types if missing
    if "is_paid" not in lt_columns:
        op.add_column("leave_types", sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "is_system_defined" not in lt_columns:
        op.add_column("leave_types", sa.Column("is_system_defined", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "is_editable" not in lt_columns:
        op.add_column("leave_types", sa.Column("is_editable", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "is_deletable" not in lt_columns:
        op.add_column("leave_types", sa.Column("is_deletable", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "annual_entitlement_days" not in lt_columns:
        op.add_column("leave_types", sa.Column("annual_entitlement_days", sa.Float(), nullable=False, server_default="0.0"))

    # Seed or backfill system-defined leaves: Unpaid Leave (UL) and Paid Leave (PL)
    # Check if UL exists
    res_ul = conn.execute(sa.text("SELECT id FROM leave_types WHERE code = 'UL' OR LOWER(name) = 'unpaid leave'")).fetchone()
    if not res_ul:
        conn.execute(sa.text("""
            INSERT INTO leave_types (name, code, unit_type, default_balance_hours, requires_approval, is_active,
                                    applicable_employee_type, carry_forward, counts_as_leave, attendance_required,
                                    remote_punch_allowed, is_paid, is_system_defined, is_editable, is_deletable, annual_entitlement_days)
            VALUES ('Unpaid Leave', 'UL', 'full_day', 96.0, true, true,
                    'all', false, true, false,
                    false, false, true, false, false, 12.0)
        """))
    else:
        conn.execute(sa.text("""
            UPDATE leave_types
            SET is_paid = false, is_system_defined = true, is_editable = false, is_deletable = false, annual_entitlement_days = 12.0
            WHERE id = :ul_id
        """), {"ul_id": res_ul[0]})

    # Check if PL exists
    res_pl = conn.execute(sa.text("SELECT id FROM leave_types WHERE code = 'PL' OR LOWER(name) = 'paid leave'")).fetchone()
    if not res_pl:
        conn.execute(sa.text("""
            INSERT INTO leave_types (name, code, unit_type, default_balance_hours, requires_approval, is_active,
                                    applicable_employee_type, carry_forward, counts_as_leave, attendance_required,
                                    remote_punch_allowed, is_paid, is_system_defined, is_editable, is_deletable, annual_entitlement_days)
            VALUES ('Paid Leave', 'PL', 'full_day', 144.0, true, true,
                    'all', false, true, false,
                    false, true, true, true, false, 18.0)
        """))
    else:
        conn.execute(sa.text("""
            UPDATE leave_types
            SET is_paid = true, is_system_defined = true, is_editable = true, is_deletable = false, annual_entitlement_days = 18.0
            WHERE id = :pl_id
        """), {"pl_id": res_pl[0]})


def downgrade():
    op.drop_column("leave_types", "annual_entitlement_days")
    op.drop_column("leave_types", "is_deletable")
    op.drop_column("leave_types", "is_editable")
    op.drop_column("leave_types", "is_system_defined")
    op.drop_column("leave_types", "is_paid")
