"""add yearly leave balances and wfh rules

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-12 11:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c5d6e7f8a9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create employee_leave_balances table
    op.create_table(
        'employee_leave_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('leave_type_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('allocated_days', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('used_days', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('pending_days', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('available_days', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('carry_forward_days', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['leave_type_id'], ['leave_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'leave_type_id', 'year', name='uq_emp_leave_year')
    )
    op.create_index('ix_employee_leave_balances_id', 'employee_leave_balances', ['id'], unique=False)
    op.create_index('ix_employee_leave_balances_employee_id', 'employee_leave_balances', ['employee_id'], unique=False)
    op.create_index('ix_employee_leave_balances_leave_type_id', 'employee_leave_balances', ['leave_type_id'], unique=False)
    op.create_index('ix_employee_leave_balances_year', 'employee_leave_balances', ['year'], unique=False)
    op.create_index('ix_emp_leave_year', 'employee_leave_balances', ['employee_id', 'year'], unique=False)

    # 2. Add fields to leave_types
    op.add_column('leave_types', sa.Column('applicable_employee_type', sa.String(length=50), nullable=False, server_default='all'))
    op.add_column('leave_types', sa.Column('carry_forward', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('leave_types', sa.Column('max_consecutive_days', sa.Integer(), nullable=True))
    op.add_column('leave_types', sa.Column('counts_as_leave', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('leave_types', sa.Column('attendance_required', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('leave_types', sa.Column('remote_punch_allowed', sa.Boolean(), nullable=False, server_default='false'))

    # 3. Add fields to timeoff_requests
    op.add_column('timeoff_requests', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('timeoff_requests', sa.Column('end_date', sa.Date(), nullable=True))
    op.add_column('timeoff_requests', sa.Column('total_days', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('timeoff_requests', 'total_days')
    op.drop_column('timeoff_requests', 'end_date')
    op.drop_column('timeoff_requests', 'start_date')

    op.drop_column('leave_types', 'remote_punch_allowed')
    op.drop_column('leave_types', 'attendance_required')
    op.drop_column('leave_types', 'counts_as_leave')
    op.drop_column('leave_types', 'max_consecutive_days')
    op.drop_column('leave_types', 'carry_forward')
    op.drop_column('leave_types', 'applicable_employee_type')

    op.drop_index('ix_emp_leave_year', table_name='employee_leave_balances')
    op.drop_index('ix_employee_leave_balances_year', table_name='employee_leave_balances')
    op.drop_index('ix_employee_leave_balances_leave_type_id', table_name='employee_leave_balances')
    op.drop_index('ix_employee_leave_balances_employee_id', table_name='employee_leave_balances')
    op.drop_index('ix_employee_leave_balances_id', table_name='employee_leave_balances')
    op.drop_table('employee_leave_balances')
