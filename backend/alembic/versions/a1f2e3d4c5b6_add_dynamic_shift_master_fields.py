"""add_dynamic_shift_master_fields

Revision ID: a1f2e3d4c5b6
Revises: c8a9e0b1d2f3
Create Date: 2026-08-05 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1f2e3d4c5b6'
down_revision: Union[str, Sequence[str], None] = 'c8a9e0b1d2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add columns to shifts table
    op.add_column('shifts', sa.Column('working_hours', sa.Numeric(precision=4, scale=2), server_default='8.0', nullable=True))
    op.add_column('shifts', sa.Column('lunch_duration_minutes', sa.Integer(), server_default='40', nullable=True))
    op.add_column('shifts', sa.Column('lunch_start_time', sa.Time(), nullable=True))
    op.add_column('shifts', sa.Column('lunch_end_time', sa.Time(), nullable=True))
    op.add_column('shifts', sa.Column('half_day_hours', sa.Numeric(precision=4, scale=2), server_default='4.0', nullable=True))
    op.add_column('shifts', sa.Column('present_hours', sa.Numeric(precision=4, scale=2), server_default='8.0', nullable=True))
    op.add_column('shifts', sa.Column('minimum_present_minutes', sa.Integer(), server_default='480', nullable=True))
    op.add_column('shifts', sa.Column('overtime_start_time', sa.Time(), nullable=True))
    op.add_column('shifts', sa.Column('late_mark_after_minutes', sa.Integer(), server_default='30', nullable=True))
    op.add_column('shifts', sa.Column('early_exit_before_minutes', sa.Integer(), server_default='0', nullable=True))
    op.add_column('shifts', sa.Column('is_night_shift', sa.Boolean(), server_default='0', nullable=True))

    # Add shift_id to employees table
    op.add_column('employees', sa.Column('shift_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_employees_shift_id'), 'employees', ['shift_id'], unique=False)
    op.create_foreign_key('fk_employees_shift_id', 'employees', 'shifts', ['shift_id'], ['id'])

    # Add shift_id to attendance table
    op.add_column('attendance', sa.Column('shift_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_attendance_shift_id'), 'attendance', ['shift_id'], unique=False)
    op.create_foreign_key('fk_attendance_shift_id', 'attendance', 'shifts', ['shift_id'], ['id'])

def downgrade() -> None:
    op.drop_constraint('fk_attendance_shift_id', 'attendance', type_='foreignkey')
    op.drop_index(op.f('ix_attendance_shift_id'), table_name='attendance')
    op.drop_column('attendance', 'shift_id')

    op.drop_constraint('fk_employees_shift_id', 'employees', type_='foreignkey')
    op.drop_index(op.f('ix_employees_shift_id'), table_name='employees')
    op.drop_column('employees', 'shift_id')

    op.drop_column('shifts', 'is_night_shift')
    op.drop_column('shifts', 'early_exit_before_minutes')
    op.drop_column('shifts', 'late_mark_after_minutes')
    op.drop_column('shifts', 'overtime_start_time')
    op.drop_column('shifts', 'minimum_present_minutes')
    op.drop_column('shifts', 'present_hours')
    op.drop_column('shifts', 'half_day_hours')
    op.drop_column('shifts', 'lunch_end_time')
    op.drop_column('shifts', 'lunch_start_time')
    op.drop_column('shifts', 'lunch_duration_minutes')
    op.drop_column('shifts', 'working_hours')
