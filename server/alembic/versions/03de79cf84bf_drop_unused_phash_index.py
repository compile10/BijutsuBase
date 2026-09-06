"""drop unused phash index

Revision ID: 03de79cf84bf
Revises: f5aaa71a19b3
Create Date: 2026-08-30 21:10:39.631377

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '03de79cf84bf'
down_revision: Union[str, Sequence[str], None] = 'f5aaa71a19b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove the B-tree index, which cannot serve Hamming-distance searches."""
    op.drop_index(op.f('ix_files_phash'), table_name='files')


def downgrade() -> None:
    """Restore the original pHash index."""
    op.create_index(op.f('ix_files_phash'), 'files', ['phash'], unique=False)
