"""Enrich files from booru sites, trying Danbooru first and Gelbooru as a fallback."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from models.file import File, TagSource
from sources.danbooru.danbooru_client import DanbooruClient
from sources.danbooru.enrich_file import apply_danbooru_post
from sources.gelbooru.enrich_file import apply_gelbooru_metadata, fetch_gelbooru_metadata
from sources.tag_utils import remove_tags_from_file

logger = logging.getLogger(__name__)


async def enrich_file_from_boorus(file: File, db: AsyncSession) -> bool:
    """Apply booru metadata to a newly uploaded file.

    Args:
        file: The File model instance to enrich
        db: AsyncSession for database operations

    Returns:
        True if metadata from Danbooru or Gelbooru was applied, False if neither had the file

    Raises:
        ValueError: If Danbooru returns multiple posts for the same MD5 hash
    """
    return await _apply_booru_metadata(file, db, replace_existing_tags=False) is not None


async def refetch_file_from_boorus(file: File, db: AsyncSession) -> TagSource | None:
    """Re-fetch booru metadata for a stored file, replacing its existing tags.

    Existing tag associations are only cleared once a matching post is found, so a
    miss leaves the file's current metadata untouched.

    Args:
        file: The File model instance to refresh
        db: AsyncSession for database operations

    Returns:
        The source that supplied the metadata, or None if no booru had the file

    Raises:
        ValueError: If Danbooru returns multiple posts for the same MD5 hash
    """
    return await _apply_booru_metadata(file, db, replace_existing_tags=True)


async def _apply_booru_metadata(
    file: File,
    db: AsyncSession,
    replace_existing_tags: bool,
) -> TagSource | None:
    danbooru_posts = await DanbooruClient().get_post(file.md5_hash)
    if len(danbooru_posts) > 1:
        raise ValueError("Multiple posts found for the same MD5 hash")

    if danbooru_posts:
        if replace_existing_tags:
            await remove_tags_from_file(file, db)
        await apply_danbooru_post(file, db, danbooru_posts[0])
        return TagSource.DANBOORU

    logger.info(f"Danbooru lookup missed for {file.sha256_hash}, trying Gelbooru")

    gelbooru_metadata = await fetch_gelbooru_metadata(file.md5_hash)
    if gelbooru_metadata is not None:
        if replace_existing_tags:
            await remove_tags_from_file(file, db)
        await apply_gelbooru_metadata(file, db, gelbooru_metadata)
        return TagSource.GELBOORU

    return None
