"""Ensure Manager role exists in roles table.

Revision ID: fd3e4f5a6b7c
Revises: fb2c3d4e5f60
Create Date: 2026-09-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select

revision: str = "fd3e4f5a6b7c"
down_revision: Union[str, Sequence[str], None] = ("fb2c3d4e5f60", "d1e2f3a4b5c6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

roles_table = table(
    "roles",
    column("id", sa.Integer),
    column("name", sa.String),
)

def upgrade() -> None:
    conn = op.get_bind()
    # Check if Manager role already exists
    res = conn.execute(
        select(roles_table.c.id).where(sa.func.lower(roles_table.c.name) == "manager")
    ).first()
    if not res:
        conn.execute(
            roles_table.insert().values(name="Manager")
        )

def downgrade() -> None:
    pass
