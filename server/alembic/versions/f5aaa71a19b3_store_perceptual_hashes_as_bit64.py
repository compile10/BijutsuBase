"""store perceptual hashes as bit64

Revision ID: f5aaa71a19b3
Revises: f6a7b8c9d0e1
Create Date: 2026-08-30 20:47:10.655119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f5aaa71a19b3'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Preserve all 64 bits, including the high-order bit and null values."""
    op.alter_column(
        'files', 'phash',
        existing_type=sa.BIGINT(),
        type_=postgresql.BIT(length=64),
        existing_nullable=True,
        postgresql_using='phash::bit(64)',
    )
    op.alter_column(
        'files', 'phash_center_80',
        existing_type=sa.BIGINT(),
        type_=postgresql.BIT(length=64),
        existing_nullable=True,
        postgresql_using='phash_center_80::bit(64)',
    )
    op.alter_column(
        'files', 'phash_center_50',
        existing_type=sa.BIGINT(),
        type_=postgresql.BIT(length=64),
        existing_nullable=True,
        postgresql_using='phash_center_50::bit(64)',
    )


def downgrade() -> None:
    """Restore the same bit patterns as signed BIGINT values."""
    op.alter_column(
        'files', 'phash_center_50',
        existing_type=postgresql.BIT(length=64),
        type_=sa.BIGINT(),
        existing_nullable=True,
        postgresql_using='phash_center_50::bigint',
    )
    op.alter_column(
        'files', 'phash_center_80',
        existing_type=postgresql.BIT(length=64),
        type_=sa.BIGINT(),
        existing_nullable=True,
        postgresql_using='phash_center_80::bigint',
    )
    op.alter_column(
        'files', 'phash',
        existing_type=postgresql.BIT(length=64),
        type_=sa.BIGINT(),
        existing_nullable=True,
        postgresql_using='phash::bigint',
    )
