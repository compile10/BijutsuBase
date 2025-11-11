"""Functions for enriching File models with Danbooru metadata."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.file import File, Rating
from models.tag import Tag, TagCategory, FileTag
from .danbooru_client import DanbooruClient, DanbooruPost

if TYPE_CHECKING:
    pass


async def make_danbooru_request(
    db: AsyncSession,
    file: File
) -> bool:
    """Make a Danbooru API request and enrich the file with metadata.
    
    Creates a Danbooru client, fetches post information, and calls
    the enrichment functions to set rating, source, and tags.
    
    Args:
        db: AsyncSession for database operations
        file: The File model instance to enrich
        
    Returns:
        True if Danbooru metadata was successfully applied, False if file not found
        
    Raises:
        ValueError: If multiple posts are found for the same MD5 hash
        Other exceptions from the enrichment functions are propagated
    """
    danbooru_client = DanbooruClient()
    posts = await danbooru_client.get_post(file.md5_hash)
    
    if not posts:
        # File not found on Danbooru
        return False
    
    # Validate there's exactly one post
    if len(posts) > 1:
        raise ValueError("Multiple posts found for the same MD5 hash")
    
    # Enrich file with Danbooru metadata
    set_rating_from_danbooru(file, posts)
    set_source_from_danbooru(file, posts)
    await add_tags_from_danbooru(file, db, posts)
    
    return True


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
    posts: list[DanbooruPost]
) -> AsyncSession:
    """Add tags to a File from Danbooru post data.
    
    Creates/associates tags with the file, correctly mapping tag categories.
    
    Args:
        file: The File model instance to add tags to
        db: AsyncSession for database operations
        posts: List of DanbooruPost objects (should contain exactly one post)
        
    Returns:
        The same db session for transaction management
        
    Raises:
        ValueError: If multiple posts are provided
    """
    # Validate there's exactly one post
    if len(posts) > 1:
        raise ValueError("Multiple posts found for the same MD5 hash")
    
    post = posts[0]
    
    # Map tag strings to categories
    tag_mappings = [
        (post.tag_string_general, TagCategory.GENERAL),
        (post.tag_string_artist, TagCategory.ARTIST),
        (post.tag_string_copyright, TagCategory.COPYRIGHT),
        (post.tag_string_character, TagCategory.CHARACTER),
        (post.tag_string_meta, TagCategory.META),
    ]
    
    # Process each tag string
    for tag_string, category in tag_mappings:
        if not tag_string:
            continue
        
        # Split tag string (tags are space-separated)
        tag_names = [name.strip() for name in tag_string.split() if name.strip()]
        
        for tag_name in tag_names:
            # Get or create tag
            result = await db.execute(
                select(Tag).where(Tag.name == tag_name)
            )
            tag = result.scalar_one_or_none()
            
            if tag is None:
                # Create new tag
                tag = Tag(name=tag_name, category=category)
                db.add(tag)
                await db.flush()  # Flush to get the tag ID
            
            # Check if association already exists by querying the junction table
            # This avoids lazy loading the file.tags relationship
            association_result = await db.execute(
                select(FileTag).where(
                    FileTag.file_sha256_hash == file.sha256_hash,
                    FileTag.tag_id == tag.id
                )
            )
            existing_association = association_result.scalar_one_or_none()
            
            if existing_association is None:
                # Create association directly via junction table to avoid lazy loading
                file_tag = FileTag(
                    file_sha256_hash=file.sha256_hash,
                    tag_id=tag.id
                )
                db.add(file_tag)
    
    return db


def set_rating_from_danbooru(
    file: File,
    posts: list[DanbooruPost]
) -> None:
    """Set rating on a File from Danbooru post data.
    
    This function only modifies the File object and should be called before
    adding the file to the database in a transaction.
    
    Args:
        file: The File model instance to set rating on
        posts: List of DanbooruPost objects (should contain exactly one post)
        
    Raises:
        ValueError: If multiple posts are provided
    """
    # Validate there's exactly one post
    if len(posts) > 1:
        raise ValueError("Multiple posts found for the same MD5 hash")
    
    post = posts[0]
    
    # Map and set rating
    file.rating = _map_danbooru_rating(post.rating)


def set_source_from_danbooru(
    file: File,
    posts: list[DanbooruPost]
) -> None:
    """Set source on a File from Danbooru post data.
    
    This function only modifies the File object and should be called before
    adding the file to the database in a transaction.
    
    Prefers Pixiv artwork page URL over direct image URLs when pixiv_id is available.
    
    Args:
        file: The File model instance to set source on
        posts: List of DanbooruPost objects (should contain exactly one post)
        
    Raises:
        ValueError: If multiple posts are provided
    """
    # Validate there's exactly one post
    if len(posts) > 1:
        raise ValueError("Multiple posts found for the same MD5 hash")
    
    post = posts[0]
    
    # Prefer Pixiv artwork page URL if pixiv_id is available
    if post.pixiv_id:
        file.source = f"https://www.pixiv.net/artworks/{post.pixiv_id}"
    elif post.source:
        # Fall back to the source field (may be direct image URL or other source)
        file.source = post.source

