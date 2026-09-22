"""add employee bank and statutory fields

Revision ID: d1e2f3a4b5c6
Revises: c5d6e7f8a9b0
Create Date: 2026-09-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('bank_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('bank_account_no', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('ifsc_code', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('micr_code', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('pan_number', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('uan_number', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('pf_number', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('employees') as batch_op:
        batch_op.drop_column('pf_number')
        batch_op.drop_column('uan_number')
        batch_op.drop_column('pan_number')
        batch_op.drop_column('micr_code')
        batch_op.drop_column('ifsc_code')
        batch_op.drop_column('bank_account_no')
        batch_op.drop_column('bank_name')
