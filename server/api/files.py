"""Files router for BijutsuBase API."""
from __future__ import annotations

from pathlib import Path
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func, update, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import get_db
from models.file import File as FileModel, Rating
from models.tag import Tag, FileTag, TagCategory
from models.pool import PoolMember, Pool
from models.family import FileFamily
from models.user import User
from utils.file_storage import generate_file_path
from utils.pagination import encode_cursor, decode_cursor
from utils.rating import get_allowed_ratings
from api.serializers.file import FileResponse, FileThumb, BulkFileRequest, BulkUpdateFileRequest, FileSearchResponse
from api.serializers.tag import TagResponse
from auth.users import current_active_user


router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)


class FileRatingUpdate(BaseModel):
    """Request model for updating file rating."""
    rating: str


class FileAiGeneratedUpdate(BaseModel):
    """Request model for updating file ai_generated status."""
    ai_generated: bool


@router.get("/search", response_model=FileSearchResponse, status_code=status.HTTP_200_OK)
async def search_files(
    tags: str = Query("", description="Space-separated list of tag names"),
    sort: str = Query("date_desc", description="Sort order: date_desc, date_asc, size_desc, size_asc, random, pool_order"),
    seed: str = Query(None, description="Seed for random sorting"),
    limit: int = Query(60, ge=1, le=200, description="Number of items to return per page"),
    cursor: str = Query(None, description="Pagination cursor from previous response"),
    max_rating: str = Query(None, description="Maximum rating to show (safe, sensitive, questionable, explicit)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Search for files that contain ALL of the specified tags with cursor-based pagination.
    
    Args:
        tags: Space-separated list of tag names to search for (supports rating:X syntax)
        sort: Sort order (date_desc, date_asc, size_desc, size_asc, random, pool_order)
        seed: Seed for random sorting (required if sort is random)
        limit: Number of items to return (max 200)
        cursor: Pagination cursor for fetching next page
        max_rating: Maximum rating to show (safe, sensitive, questionable, explicit)
        db: Database session
        
    Returns:
        FileSearchResponse with items, next_cursor, and has_more flag
    """
    # Split space-separated tag names and filter out empty strings
    raw_tag_names = [tag.strip() for tag in tags.split() if tag.strip()]
    pool_id: uuid.UUID | None = None
    tag_names: list[str] = []
    excluded_tag_names: list[str] = []
    rating_from_tag: str | None = None
    category_filters: list[TagCategory] = []
    excluded_categories: list[TagCategory] = []
    excluded_pool_ids: list[uuid.UUID] = []
    
    for tag in raw_tag_names:
        if tag.lower().startswith("pool:"):
            try:
                pool_id = uuid.UUID(tag.split(":", 1)[1])
            except (ValueError, IndexError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid pool identifier. Expected pool:<UUID>."
                )
        elif tag.lower().startswith("-pool:"):
            # Exclude pool
            try:
                excluded_pool_ids.append(uuid.UUID(tag.split(":", 1)[1]))
            except (ValueError, IndexError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid pool identifier. Expected -pool:<UUID>."
                )
        elif tag.lower().startswith("rating:"):
            try:
                rating_from_tag = tag.split(":", 1)[1].lower()
            except IndexError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid rating filter. Expected rating:<rating_value>."
                )
        elif tag.lower().startswith("-tag:"):
            # Exclude category
            cat_name = tag.split(":", 1)[1].lower()
            try:
                excluded_categories.append(TagCategory(cat_name))
            except ValueError:
                valid_categories = [c.value for c in TagCategory]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tag category. Must be one of: {', '.join(valid_categories)}"
                )
        elif tag.lower().startswith("tag:"):
            # Include category filter
            cat_name = tag.split(":", 1)[1].lower()
            try:
                category_filters.append(TagCategory(cat_name))
            except ValueError:
                valid_categories = [c.value for c in TagCategory]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tag category. Must be one of: {', '.join(valid_categories)}"
                )
        elif tag.startswith("-") and len(tag) > 1:
            # Negative tag - exclude files with this tag
            excluded_tag_names.append(tag[1:])
        else:
            tag_names.append(tag)
    
    # Rating tag overrides query parameter if both are provided
    effective_max_rating = rating_from_tag if rating_from_tag is not None else max_rating
    
    # Validate and prepare rating filter
    allowed_ratings: list[Rating] | None = None
    if effective_max_rating:
        allowed_ratings = get_allowed_ratings(effective_max_rating)
        if allowed_ratings is None:
            valid_ratings = [r.value for r in Rating]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rating. Must be one of: {', '.join(valid_ratings)}"
            )
    
    # Decode cursor if provided
    cursor_sort_value = None
    cursor_sha256 = None
    if cursor:
        cursor_sort_value, cursor_sha256 = decode_cursor(cursor)
    
    # Determine sort field and direction
    if sort == "date_desc":
        sort_field = FileModel.date_added
        sort_order = "desc"
    elif sort == "date_asc":
        sort_field = FileModel.date_added
        sort_order = "asc"
    elif sort == "size_desc":
        sort_field = FileModel.file_size
        sort_order = "desc"
    elif sort == "size_asc":
        sort_field = FileModel.file_size
        sort_order = "asc"
    elif sort == "random":
        if not seed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seed is required for random sorting."
            )
        else:
            # Deterministic random sort using MD5 of hash + seed
            sort_field = func.md5(FileModel.sha256_hash + seed)
            sort_order = "asc"  # Direction doesn't strictly matter for random, but we need one
    elif sort == "pool_order":
        # Sort by pool member order (requires pool_id to be set)
        if not pool_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pool_order sort requires a pool: tag."
            )
        sort_field = PoolMember.order
        sort_order = "asc"
    else:
        # Default to date_desc if invalid sort param provided
        sort_field = FileModel.date_added
        sort_order = "desc"

    # Build base query
    if tag_names:
        # Query files that have ALL of the specified tags
        # We need to select both the hash and the sort field for cursor filtering
        query = (
            select(FileModel.sha256_hash, sort_field)
            .join(FileTag, FileModel.sha256_hash == FileTag.file_sha256_hash)
            .join(Tag, FileTag.tag_id == Tag.id)
            .where(Tag.name.in_(tag_names))
        )
    else:
        # If no tags provided, return all files
        query = select(FileModel.sha256_hash, sort_field)
    
    # Add pool join if pool_id is specified
    if pool_id:
        query = query.join(PoolMember, PoolMember.file_sha256_hash == FileModel.sha256_hash)
        query = query.where(PoolMember.pool_id == pool_id)
    
    # Apply rating filter if specified
    if allowed_ratings:
        query = query.where(FileModel.rating.in_(allowed_ratings))
    
    # Apply grouping if we have tag filters
    if tag_names:
        query = query.group_by(FileModel.sha256_hash, sort_field)
        query = query.having(func.count(func.distinct(Tag.id)) == len(tag_names))
    
    # Apply exclusion filter for negative tags
    if excluded_tag_names:
        excluded_exists = (
            exists()
            .where(FileTag.file_sha256_hash == FileModel.sha256_hash)
            .where(FileTag.tag_id == Tag.id)
            .where(Tag.name.in_(excluded_tag_names))
        )
        query = query.where(~excluded_exists)
    
    # Apply category inclusion filter (files must have at least one tag in each category)
    for cat in category_filters:
        cat_exists = (
            exists()
            .where(FileTag.file_sha256_hash == FileModel.sha256_hash)
            .where(FileTag.tag_id == Tag.id)
            .where(Tag.category == cat)
        )
        query = query.where(cat_exists)
    
    # Apply category exclusion filter (files must not have any tags in each category)
    for cat in excluded_categories:
        cat_exists = (
            exists()
            .where(FileTag.file_sha256_hash == FileModel.sha256_hash)
            .where(FileTag.tag_id == Tag.id)
            .where(Tag.category == cat)
        )
        query = query.where(~cat_exists)
    
    # Apply pool exclusion filter
    for excl_pool_id in excluded_pool_ids:
        pool_exists = (
            exists()
            .where(PoolMember.file_sha256_hash == FileModel.sha256_hash)
            .where(PoolMember.pool_id == excl_pool_id)
        )
        query = query.where(~pool_exists)
    
    # Apply cursor-based filtering
    if cursor_sort_value is not None and cursor_sha256 is not None:
        if sort_order == "desc":
            # For descending order: (sort_field, sha256) < (cursor_sort, cursor_sha256)
            query = query.where(
                (sort_field < cursor_sort_value) |
                ((sort_field == cursor_sort_value) & (FileModel.sha256_hash < cursor_sha256))
            )
        else:
            # For ascending order: (sort_field, sha256) > (cursor_sort, cursor_sha256)
            query = query.where(
                (sort_field > cursor_sort_value) |
                ((sort_field == cursor_sort_value) & (FileModel.sha256_hash > cursor_sha256))
            )
    
    # Apply ordering
    if sort_order == "desc":
        query = query.order_by(sort_field.desc(), FileModel.sha256_hash.desc())
    else:
        query = query.order_by(sort_field.asc(), FileModel.sha256_hash.asc())
    
    # Fetch limit + 1 to determine if there are more results
    query = query.limit(limit + 1)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Check if there are more results
    has_more = len(rows) > limit
    items = rows[:limit]  # Take only the requested limit
    
    # Convert to FileThumb objects
    file_thumbs = [
        FileThumb.model_validate({'sha256_hash': item[0]})
        for item in items
    ]
    
    # Generate next cursor if there are more results
    next_cursor = None
    if has_more and items:
        last_row = items[-1]
        next_cursor = encode_cursor(last_row[1], last_row[0])
    
    return FileSearchResponse(
        items=file_thumbs,
        next_cursor=next_cursor,
        has_more=has_more
    )


@router.post("/bulk-common-tags", response_model=list[TagResponse], status_code=status.HTTP_200_OK)
async def get_common_tags(
    request: BulkFileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Get tags common to all specified files.

    Args:
        request: BulkFileRequest containing list of file hashes
        db: Database session

    Returns:
        List of TagResponse objects representing the intersection of tags
    """
    if not request.file_hashes:
        return []

    # Find tags where the count of associations with the given files equals the number of files
    query = (
        select(Tag)
        .join(FileTag, Tag.id == FileTag.tag_id)
        .where(FileTag.file_sha256_hash.in_(request.file_hashes))
        .group_by(Tag.id)
        .having(func.count(FileTag.file_sha256_hash) == len(request.file_hashes))
    )

    result = await db.execute(query)
    tags = result.scalars().all()
    
    return [TagResponse.model_validate(tag) for tag in tags]


@router.post("/bulk-update", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_update_files(
    request: BulkUpdateFileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Bulk update metadata (rating, ai_generated) for multiple files.

    Args:
        request: BulkUpdateFileRequest containing hashes and fields to update
        db: Database session
    """
    if not request.file_hashes:
        return

    update_values = {}
    if request.rating is not None:
        try:
            update_values["rating"] = Rating(request.rating.lower())
        except ValueError:
            valid_ratings = [r.value for r in Rating]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rating. Must be one of: {', '.join(valid_ratings)}"
            )
            
    if request.ai_generated is not None:
        update_values["ai_generated"] = request.ai_generated

    if not update_values:
        return

    try:
        stmt = (
            update(FileModel)
            .where(FileModel.sha256_hash.in_(request.file_hashes))
            .values(**update_values)
            .execution_options(synchronize_session=False)
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to bulk update files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update files: {str(e)}"
        )


@router.get("/{sha256}", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def get_file(
    sha256: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Fetch a file by its SHA-256 hash and return serialized details including tags."""
    result = await db.execute(
        select(FileModel)
        .options(
            selectinload(FileModel.tags),
            selectinload(FileModel.pool_entries)
            .selectinload(PoolMember.pool)
            .selectinload(Pool.members)
            .selectinload(PoolMember.file),
            selectinload(FileModel.family_as_child).selectinload(FileFamily.parent),
            selectinload(FileModel.family_as_parent).selectinload(FileFamily.children)
        )
        .where(FileModel.sha256_hash == sha256)
    )
    file_model = result.scalar_one_or_none()
    if file_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse.model_validate(file_model)


@router.patch("/rating/{sha256}", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def update_file_rating(
    sha256: str,
    rating_update: FileRatingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Update the rating of a file by its SHA-256 hash."""
    # Validate and convert rating string to Rating enum
    try:
        new_rating = Rating(rating_update.rating.lower())
    except ValueError:
        valid_ratings = [r.value for r in Rating]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rating. Must be one of: {', '.join(valid_ratings)}"
        )

    # Update the rating with row locking to prevent race conditions
    try:
        # Lock the row for update
        result = await db.execute(
            select(FileModel)
            .where(FileModel.sha256_hash == sha256)
            .with_for_update()
        )
        file_model = result.scalar_one_or_none()
        
        if file_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        
        # Update the rating while row is locked
        file_model.rating = new_rating
        await db.flush()
        await db.commit()
        
        # Re-fetch with all relationships for response
        result = await db.execute(
            select(FileModel)
            .options(
                selectinload(FileModel.tags),
                selectinload(FileModel.pool_entries).selectinload(PoolMember.pool),
                selectinload(FileModel.family_as_child),
                selectinload(FileModel.family_as_parent)
            )
            .where(FileModel.sha256_hash == sha256)
        )
        file_model = result.scalar_one()
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update rating for file {sha256}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file rating: {str(e)}"
        )

    return FileResponse.model_validate(file_model)


@router.patch("/ai_generated/{sha256}", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def update_file_ai_generated(
    sha256: str,
    ai_generated_update: FileAiGeneratedUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Update the ai_generated status of a file by its SHA-256 hash."""
    # Update the status with row locking to prevent race conditions
    try:
        # Lock the row for update
        result = await db.execute(
            select(FileModel)
            .where(FileModel.sha256_hash == sha256)
            .with_for_update()
        )
        file_model = result.scalar_one_or_none()
        
        if file_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        
        # Update the status while row is locked
        file_model.ai_generated = ai_generated_update.ai_generated
        await db.flush()
        await db.commit()
        
        # Re-fetch with all relationships for response
        result = await db.execute(
            select(FileModel)
            .options(
                selectinload(FileModel.tags),
                selectinload(FileModel.pool_entries).selectinload(PoolMember.pool),
                selectinload(FileModel.family_as_child),
                selectinload(FileModel.family_as_parent)
            )
            .where(FileModel.sha256_hash == sha256)
        )
        file_model = result.scalar_one()
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update ai_generated for file {sha256}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file ai_generated status: {str(e)}"
        )

    return FileResponse.model_validate(file_model)


@router.delete("/{sha256}", status_code=status.HTTP_200_OK)
async def delete_file(
    sha256: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Delete a file by its SHA-256 hash."""
    result = await db.execute(select(FileModel).where(FileModel.sha256_hash == sha256))
    file_model = result.scalar_one_or_none()
    if file_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    try:
        # Delete association rows via ORM to trigger tag count decrements
        from models.tag import FileTag

        assoc_result = await db.execute(
            select(FileTag).where(FileTag.file_sha256_hash == sha256)
        )
        associations = assoc_result.scalars().all()
        for assoc in associations:
            await db.delete(assoc)
        
        # Delete the file record; after_delete hook removes files from disk
        await db.delete(file_model)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete file: {str(e)}")

    return {"ok": True}
