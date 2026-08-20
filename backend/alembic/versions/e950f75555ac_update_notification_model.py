"""update_notification_model

Revision ID: e950f75555ac
Revises: d576047fa37a
Create Date: 2026-06-30 12:58:04.961842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e950f75555ac'
down_revision: Union[str, Sequence[str], None] = 'd576047fa37a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('notifications')]

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        if 'category' not in columns:
            batch_op.add_column(sa.Column('category', sa.String(length=50), nullable=True))
        if 'severity' not in columns:
            batch_op.add_column(sa.Column('severity', sa.String(length=20), nullable=True))
        if 'employee_id' not in columns:
            batch_op.add_column(sa.Column('employee_id', sa.Integer(), nullable=True))
        if 'created_by' not in columns:
            batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        if 'receiver_role' not in columns:
            batch_op.add_column(sa.Column('receiver_role', sa.String(length=50), nullable=True))
        if 'updated_at' not in columns:
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
        if 'deleted_at' not in columns:
            batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'notification_metadata' not in columns:
            batch_op.add_column(sa.Column('notification_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('notifications')]

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        for col in ['notification_metadata', 'deleted_at', 'updated_at', 'receiver_role', 'created_by', 'employee_id', 'severity', 'category']:
            if col in columns:
                batch_op.drop_column(col)
