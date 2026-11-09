"""Shared helpers for applying externally sourced tags to files."""

import logging
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.file import File
from models.tag import FileTag, Tag, TagCategory

logger = logging.getLogger(__name__)

TAG_NAME_MAX_LENGTH: int = Tag.__table__.c.name.type.length


async def associate_tags(
    file: File,
    db: AsyncSession,
    tag_names: Iterable[str],
    category: TagCategory,
) -> None:
    """Create (if needed) and associate tags with a file.

    Tags that already exist keep their stored category; `category` only applies
    to newly created tags. Duplicate associations are ignored. Names longer than
    the `tags.name` column are skipped so one oversized tag cannot abort enrichment.

    Args:
        file: The File model instance to tag
        db: AsyncSession for database operations
        tag_names: Tag names to associate
        category: Category for tags that do not exist yet
    """
    for tag_name in tag_names:
        if len(tag_name) > TAG_NAME_MAX_LENGTH:
            logger.warning(
                f"Skipping tag longer than {TAG_NAME_MAX_LENGTH} characters for {file.sha256_hash}: {tag_name[:40]}..."
            )
            continue

        tag: Tag | None = None
        try:
            async with db.begin_nested():
                tag = Tag(name=tag_name, category=category)
                db.add(tag)
        except IntegrityError:
            tag = await db.scalar(select(Tag).where(Tag.name == tag_name))
            if tag is None:
                raise

        try:
            async with db.begin_nested():
                db.add(FileTag(file_sha256_hash=file.sha256_hash, tag_id=tag.id))
        except IntegrityError:
            continue


async def remove_tags_from_file(file: File, db: AsyncSession) -> None:
    """Delete every tag association for a file.

    Associations are deleted through the ORM so the `FileTag` delete events keep
    tag counts accurate and prune orphaned tags.

    Args:
        file: The File model instance to strip tags from
        db: AsyncSession for database operations
    """
    result = await db.execute(
        select(FileTag).where(FileTag.file_sha256_hash == file.sha256_hash)
    )

    for association in result.scalars().all():
        await db.delete(association)

    await db.flush()
