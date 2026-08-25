"""add_office_geofencing_fields

Revision ID: f8a9b0c1d2e3
Revises: 099d48fab4c9
Create Date: 2026-08-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add geofencing fields to work_locations table
    op.add_column('work_locations', sa.Column('location_type', sa.String(length=50), nullable=False, server_default='office'))
    op.add_column('work_locations', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('work_locations', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('work_locations', sa.Column('geofence_radius_meters', sa.Float(), nullable=False, server_default='40.0'))

    # Batch mode keeps the foreign-key alteration compatible with SQLite.
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.add_column(sa.Column('work_location_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('work_location_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('geofence_distance_meters', sa.Float(), nullable=True))
        batch_op.create_foreign_key('fk_attendance_work_location', 'work_locations', ['work_location_id'], ['id'])
        batch_op.create_index(op.f('ix_attendance_work_location_id'), ['work_location_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_attendance_work_location_id'))
        batch_op.drop_constraint('fk_attendance_work_location', type_='foreignkey')
        batch_op.drop_column('geofence_distance_meters')
        batch_op.drop_column('work_location_name')
        batch_op.drop_column('work_location_id')
    op.drop_column('work_locations', 'geofence_radius_meters')
    op.drop_column('work_locations', 'longitude')
    op.drop_column('work_locations', 'latitude')
    op.drop_column('work_locations', 'location_type')
