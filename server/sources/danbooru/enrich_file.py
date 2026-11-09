"""Functions for enriching File models with Danbooru metadata."""
from sqlalchemy.ext.asyncio import AsyncSession

from models.file import File, Rating, TagSource
from models.tag import TagCategory
from sources.tag_utils import associate_tags
from api.serializers.danbooru import DanbooruPost


async def apply_danbooru_post(
    file: File,
    db: AsyncSession,
    post: DanbooruPost,
) -> None:
    """Set rating, source, tags, and tag source on a file from a Danbooru post.

    Args:
        file: The File model instance to enrich
        db: AsyncSession for database operations
        post: The Danbooru post matching the file
    """
    set_rating_from_danbooru(file, post)
    set_source_from_danbooru(file, post)
    await add_tags_from_danbooru(file, db, post)
    file.tag_source = TagSource.DANBOORU


def _map_danbooru_rating(danbooru_rating: str | None) -> Rating:
    """Map Danbooru rating string to Rating enum.

    Args:
        danbooru_rating: Danbooru rating string (g, s, q, e) or None

    Returns:
        Rating enum value
    """
    if danbooru_rating == "g":
        return Rating.SAFE
    elif danbooru_rating == "s":
        return Rating.SENSITIVE
    elif danbooru_rating == "q":
        return Rating.QUESTIONABLE
    elif danbooru_rating == "e":
        return Rating.EXPLICIT
    else:
        # Default to EXPLICIT if unknown or None
        return Rating.EXPLICIT


async def add_tags_from_danbooru(
    file: File,
    db: AsyncSession,
    post: DanbooruPost,
) -> None:
    """Add tags to a File from Danbooru post data, mapping tag categories.

    Args:
        file: The File model instance to add tags to
        db: AsyncSession for database operations
        post: The Danbooru post matching the file
    """
    tag_mappings = [
        (post.tag_string_general, TagCategory.GENERAL),
        (post.tag_string_artist, TagCategory.ARTIST),
        (post.tag_string_copyright, TagCategory.COPYRIGHT),
        (post.tag_string_character, TagCategory.CHARACTER),
        (post.tag_string_meta, TagCategory.META),
    ]

    for tag_string, category in tag_mappings:
        await associate_tags(file, db, tag_string.split(), category)


def set_rating_from_danbooru(file: File, post: DanbooruPost) -> None:
    """Set rating on a File from Danbooru post data.

    Args:
        file: The File model instance to set rating on
        post: The Danbooru post matching the file
    """
    file.rating = _map_danbooru_rating(post.rating)


def set_source_from_danbooru(file: File, post: DanbooruPost) -> None:
    """Set source on a File from Danbooru post data.

    Prefers Pixiv artwork page URL over direct image URLs when pixiv_id is available.

    Args:
        file: The File model instance to set source on
        post: The Danbooru post matching the file
    """
    if post.pixiv_id:
        file.source = f"https://www.pixiv.net/artworks/{post.pixiv_id}"
    elif post.source:
        # Fall back to the source field (may be direct image URL or other source)
        file.source = post.source
