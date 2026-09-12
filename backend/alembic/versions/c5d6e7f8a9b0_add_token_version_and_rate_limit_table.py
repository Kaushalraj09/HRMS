"""add token version and rate limit table

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-12 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5d6e7f8a9b0'
down_revision = 'b4c5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add token_version and last_login_ip to users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('last_login_ip', sa.String(length=50), nullable=True))

    # 2. Create rate_limit_records table
    op.create_table(
        'rate_limit_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rate_limit_records_id', 'rate_limit_records', ['id'], unique=False)
    op.create_index('ix_rate_limit_records_key', 'rate_limit_records', ['key'], unique=True)
    op.create_index('ix_rate_limit_key_locked', 'rate_limit_records', ['key', 'locked_until'], unique=False)


def downgrade():
    op.drop_index('ix_rate_limit_key_locked', table_name='rate_limit_records')
    op.drop_index('ix_rate_limit_records_key', table_name='rate_limit_records')
    op.drop_index('ix_rate_limit_records_id', table_name='rate_limit_records')
    op.drop_table('rate_limit_records')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('last_login_ip')
        batch_op.drop_column('token_version')
