"""merge training and geofencing migration heads

Revision ID: fa1b2c3d4e5f
Revises: f3e4d5c6b7a8, f8a9b0c1d2e3
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op


revision: str = "fa1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = ("f3e4d5c6b7a8", "f8a9b0c1d2e3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the two feature branches without changing their schema."""
    pass


def downgrade() -> None:
    """Re-expose the two historical heads when rolling back this merge."""
    pass
