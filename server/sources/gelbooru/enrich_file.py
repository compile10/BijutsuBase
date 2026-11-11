"""Functions for enriching File models with Gelbooru metadata."""
import html
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from models.file import File, Rating, TagSource
from models.tag import TagCategory
from sources.tag_utils import associate_tags
from .gelbooru_client import GelbooruClient
from api.serializers.gelbooru import GelbooruPost

# Gelbooru tag types share Danbooru's numbering; deprecated (6) and unknown
# types fall back to general
GELBOORU_TAG_TYPE_CATEGORIES: dict[int, TagCategory] = {
    0: TagCategory.GENERAL,
    1: TagCategory.ARTIST,
    3: TagCategory.COPYRIGHT,
    4: TagCategory.CHARACTER,
    5: TagCategory.META,
}

GELBOORU_RATINGS: dict[str, Rating] = {
    "general": Rating.SAFE,
    "safe": Rating.SAFE,
    "sensitive": Rating.SENSITIVE,
    "questionable": Rating.QUESTIONABLE,
    "explicit": Rating.EXPLICIT,
}


@dataclass(frozen=True)
class GelbooruMetadata:
    """A Gelbooru post together with the categories of its tags."""

    post: GelbooruPost
    tags_by_category: dict[TagCategory, list[str]]


async def fetch_gelbooru_metadata(md5: str) -> GelbooruMetadata | None:
    """Look up the Gelbooru post for an MD5 hash and categorize its tags.

    Args:
        md5: The MD5 hash of the file

    Returns:
        The post and its categorized tags, or None if Gelbooru has no post for the hash

    Raises:
        GelbooruNotConfiguredError: If Gelbooru credentials are not configured
        GelbooruApiError: If the post or tag category lookup fails
    """
    client = GelbooruClient()
    posts = await client.get_post(md5)

    if not posts:
        return None

    post = posts[0]
    tag_names = get_gelbooru_tag_names(post)

    tag_types = await client.get_tag_types(tag_names)

    return GelbooruMetadata(
        post=post,
        tags_by_category=categorize_gelbooru_tags(tag_names, tag_types),
    )


async def apply_gelbooru_metadata(
    file: File,
    db: AsyncSession,
    metadata: GelbooruMetadata,
) -> None:
    """Set rating, source, tags, and tag source on a file from Gelbooru metadata.

    Args:
        file: The File model instance to enrich
        db: AsyncSession for database operations
        metadata: The Gelbooru post and categorized tags matching the file
    """
    file.rating = GELBOORU_RATINGS.get(metadata.post.rating, Rating.EXPLICIT)

    source = get_gelbooru_source(metadata.post)
    if source:
        file.source = source

    for category, tag_names in metadata.tags_by_category.items():
        await associate_tags(file, db, tag_names, category)

    file.tag_source = TagSource.GELBOORU


def get_gelbooru_tag_names(post: GelbooruPost) -> list[str]:
    """Return the post's unescaped tag names.

    Gelbooru HTML-escapes tag strings (e.g. `&#039;` for apostrophes).
    """
    return html.unescape(post.tags).split()


def categorize_gelbooru_tags(
    tag_names: list[str],
    tag_types: dict[str, int],
) -> dict[TagCategory, list[str]]:
    """Group tag names by category using Gelbooru tag types.

    Args:
        tag_names: Tag names from the post
        tag_types: Gelbooru tag type for each known tag name

    Returns:
        Tag names grouped by category; tags without a known type are general
    """
    tags_by_category: dict[TagCategory, list[str]] = {}

    for tag_name in tag_names:
        tag_type = tag_types.get(tag_name, 0)
        category = GELBOORU_TAG_TYPE_CATEGORIES.get(tag_type, TagCategory.GENERAL)
        tags_by_category.setdefault(category, []).append(tag_name)

    return tags_by_category


def get_gelbooru_source(post: GelbooruPost) -> str | None:
    """Return the first source URL of a post.

    Gelbooru allows several space-separated sources in a single field.
    """
    if not post.source:
        return None

    sources = html.unescape(post.source).split()
    if not sources:
        return None

    return sources[0]
