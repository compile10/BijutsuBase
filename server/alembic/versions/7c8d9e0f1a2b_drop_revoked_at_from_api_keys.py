"""drop revoked_at from api_keys

Revision ID: 7c8d9e0f1a2b
Revises: 9b3c4d5e6f7a
Create Date: 2026-11-21 21:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c8d9e0f1a2b"
down_revision: Union[str, Sequence[str], None] = "9b3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unused revoked_at column from api_keys."""
    op.drop_column("api_keys", "revoked_at")


def downgrade() -> None:
    """Restore revoked_at column on api_keys."""
    op.add_column(
        "api_keys",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
