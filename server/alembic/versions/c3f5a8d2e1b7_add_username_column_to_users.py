"""add username column to users

Revision ID: c3f5a8d2e1b7
Revises: b8e4f3a2c1d9
Create Date: 2026-01-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f5a8d2e1b7'
down_revision: Union[str, Sequence[str], None] = 'b8e4f3a2c1d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user', sa.Column('username', sa.String(length=50), nullable=False))
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_column('user', 'username')
