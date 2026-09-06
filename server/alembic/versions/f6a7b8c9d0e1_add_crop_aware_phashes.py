"""add crop-aware phashes

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hashes for centered views retaining 80% and 50% of the image."""
    op.add_column(
        "files",
        sa.Column("phash_center_80", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "files",
        sa.Column("phash_center_50", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    """Remove crop-aware perceptual hashes."""
    op.drop_column("files", "phash_center_50")
    op.drop_column("files", "phash_center_80")
