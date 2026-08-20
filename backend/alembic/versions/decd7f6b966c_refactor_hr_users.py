"""refactor_hr_users

Revision ID: decd7f6b966c
Revises: 0a535eb07231
Create Date: 2026-06-27 13:38:10.368422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'decd7f6b966c'
down_revision: Union[str, Sequence[str], None] = '0a535eb07231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('hr_users')]

    with op.batch_alter_table('hr_users', schema=None) as batch_op:
        if 'hr_settings' not in columns:
            batch_op.add_column(sa.Column('hr_settings', sa.String(), nullable=True))
        
        for col in ['designation', 'hr_code', 'email', 'department', 'full_name', 'phone', 'status']:
            if col in columns:
                batch_op.drop_column(col)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('hr_users')]

    with op.batch_alter_table('hr_users', schema=None) as batch_op:
        if 'status' not in columns:
            batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True))
        if 'phone' not in columns:
            batch_op.add_column(sa.Column('phone', sa.String(length=20), nullable=True))
        if 'full_name' not in columns:
            batch_op.add_column(sa.Column('full_name', sa.String(length=150), nullable=True))
        if 'department' not in columns:
            batch_op.add_column(sa.Column('department', sa.String(length=100), nullable=True))
        if 'email' not in columns:
            batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        if 'hr_code' not in columns:
            batch_op.add_column(sa.Column('hr_code', sa.String(length=30), nullable=True))
        if 'designation' not in columns:
            batch_op.add_column(sa.Column('designation', sa.String(length=100), nullable=True))
        if 'hr_settings' in columns:
            batch_op.drop_column('hr_settings')
