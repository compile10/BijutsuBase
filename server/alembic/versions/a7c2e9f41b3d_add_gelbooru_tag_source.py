"""add gelbooru tag source

Revision ID: a7c2e9f41b3d
Revises: 03de79cf84bf
Create Date: 2026-11-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7c2e9f41b3d'
down_revision: Union[str, Sequence[str], None] = '03de79cf84bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLAlchemy stores enum names, so the new label is uppercase
    op.execute("ALTER TYPE tagsource ADD VALUE IF NOT EXISTS 'GELBOORU'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres cannot drop an enum label, so rebuild the type. Gelbooru-tagged files
    # become ONNX so they remain eligible for a booru refetch.
    op.execute("UPDATE files SET tag_source = 'ONNX' WHERE tag_source = 'GELBOORU'")
    op.execute("ALTER TABLE files ALTER COLUMN tag_source DROP DEFAULT")
    op.execute("ALTER TYPE tagsource RENAME TO tagsource_old")
    op.execute("CREATE TYPE tagsource AS ENUM ('DANBOORU', 'ONNX')")
    op.execute(
        "ALTER TABLE files ALTER COLUMN tag_source TYPE tagsource "
        "USING tag_source::text::tagsource"
    )
    op.execute("ALTER TABLE files ALTER COLUMN tag_source SET DEFAULT 'ONNX'")
    op.execute("DROP TYPE tagsource_old")
