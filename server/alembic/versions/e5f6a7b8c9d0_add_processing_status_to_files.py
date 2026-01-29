"""add processing status to files

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-01-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the ProcessingStatus enum type
    # Uses uppercase names to match SQLAlchemy's enum serialization (enum.name, not enum.value)
    processing_status_enum = sa.Enum(
        'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
        name='processingstatus'
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Add processing_status column with default 'COMPLETED' for existing files
    op.add_column(
        'files',
        sa.Column(
            'processing_status',
            processing_status_enum,
            nullable=False,
            server_default='COMPLETED'
        )
    )
    
    # Add processing_error column (nullable)
    op.add_column(
        'files',
        sa.Column(
            'processing_error',
            sa.String(length=2048),
            nullable=True
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop columns
    op.drop_column('files', 'processing_error')
    op.drop_column('files', 'processing_status')
    
    # Drop the enum type
    processing_status_enum = sa.Enum(name='processingstatus')
    processing_status_enum.drop(op.get_bind(), checkfirst=True)
