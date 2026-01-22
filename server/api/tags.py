"""Tags router for BijutsuBase API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from database.config import get_db
from models.file import File as FileModel
from models.tag import Tag, TagCategory, FileTag
from models.user import User
from api.serializers.file import FileResponse
from sources.danbooru import DanbooruClient
from api.serializers.tag import (
    TagAssociateRequest,
    TagDissociateRequest,
    BulkTagAssociateRequest,
    BulkTagDissociateRequest,
    TagBrowseResponse,
    TagResponse,
)
from utils.danbooru_utils import map_danbooru_category_int_to_str
from auth.users import current_active_user


router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("/browse", response_model=list[TagBrowseResponse], status_code=status.HTTP_200_OK)
async def browse_tags(
    category: TagCategory = Query(..., description="Tag category to browse"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Browse tags by category with pagination, sorted alphabetically.
    Each tag includes an example thumbnail from the most recently added file
    associated with the tag (if any).
    """
    file_tags_with_rn = (
        select(
            FileTag.tag_id,
            FileTag.file_sha256_hash,
            func.row_number()
            .over(
                partition_by=FileTag.tag_id,
                order_by=(FileModel.date_added.desc(), FileModel.sha256_hash.asc()),
            )
            .label("rn"),
        )
        .join(FileModel, FileTag.file_sha256_hash == FileModel.sha256_hash)
        .subquery()
    )

    latest_file_filtered = (
        select(file_tags_with_rn.c.tag_id, file_tags_with_rn.c.file_sha256_hash)
        .where(file_tags_with_rn.c.rn == 1)
        .subquery()
    )

    latest_file = aliased(latest_file_filtered)

    stmt = (
        select(
            Tag.name,
            Tag.count,
            latest_file.c.file_sha256_hash.label("example_thumbnail"),
        )
        .outerjoin(latest_file, Tag.id == latest_file.c.tag_id)
        .where(Tag.category == category)
        .order_by(Tag.name.asc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()
    return [
        TagBrowseResponse(name=row.name, count=row.count, example_thumbnail=row.example_thumbnail)
        for row in rows
    ]


@router.get("/recommend", response_model=list[str], status_code=status.HTTP_200_OK)
async def recommend_tags(
    query: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Recommend tags based on user input, ordered by how frequently they
    appear across files.

    Args:
        query: Partial tag name to search for (case-insensitive prefix match).
        limit: Maximum number of tags to return.
        db: Database session.

    Returns:
        A list of tag names ordered by descending usage count.
    """
    stmt = (
        select(Tag)
        .where(Tag.name.ilike(f"{query}%"))
        .order_by(Tag.count.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    tags = result.scalars().all()
    return [tag.name for tag in tags]


@router.get("/danbooru-recs", response_model=list[TagResponse], status_code=status.HTTP_200_OK)
async def danbooru_recommend_tags(
    query: str,
    limit: int = 20,
    user: User = Depends(current_active_user),
):
    """
    Recommend tags from Danbooru based on user input.

    Args:
        query: Partial tag name to search for.
        limit: Maximum number of tags to return.

    Returns:
        A list of TagResponse objects.
    """
    client = DanbooruClient()
    danbooru_tags = await client.search_tags(query, limit=limit)
    
    # Map DanbooruTag (with int category) to TagResponse (with str category)
    recommendations = []
    for tag in danbooru_tags:
        recommendations.append(
            TagResponse(
                name=tag.name,
                category=map_danbooru_category_int_to_str(tag.category),
                count=tag.post_count
            )
        )
        
    return recommendations


@router.post("/associate", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def associate_tag(
    request: TagAssociateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Associate a tag with a file.
    
    If the tag does not exist, create it with the provided category.
    If the tag exists, use the existing tag (ignore provided category).
    If the association already exists, handle gracefully.
    
    Uses row-level locking (SELECT FOR UPDATE) to prevent race conditions.
    
    Args:
        request: Request containing file_sha256, tag_name, and category
        db: Database session
        
    Returns:
        FileResponse with updated tags
    """
    # Verify file exists and lock the row to prevent concurrent modifications
    result = await db.execute(
        select(FileModel)
        .where(FileModel.sha256_hash == request.file_sha256)
        .with_for_update()
    )
    file_model = result.scalar_one_or_none()
    if file_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Try to create the tag; if it exists, fetch it instead
    try:
        tag_category = TagCategory(request.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join([c.value for c in TagCategory])}"
        )
    
    tag = Tag(name=request.tag_name, category=tag_category)
    db.add(tag)
    
    try:
        await db.flush()  # Flush to get the tag ID
    except IntegrityError:
        # Tag already exists (unique constraint violation), fetch it
        await db.rollback()
        tag_result = await db.execute(
            select(Tag).where(Tag.name == request.tag_name).with_for_update()
        )
        tag = tag_result.scalar_one()
    
    # Create FileTag association
    file_tag = FileTag(
        file_sha256_hash=request.file_sha256,
        tag_id=tag.id
    )
    
    try:
        db.add(file_tag)
        await db.flush()  # Flush but don't commit yet to maintain the lock
    except IntegrityError:
        # Association already exists (duplicate), rollback and continue
        # File can't be deleted due to row lock, so this must be a duplicate
        await db.rollback()
    
    # Reload file with tags (still within transaction, lock still held)
    result = await db.execute(
        select(FileModel)
        .options(selectinload(FileModel.tags))
        .where(FileModel.sha256_hash == request.file_sha256)
    )
    file_model = result.scalar_one()
    
    # Now commit to release the lock
    await db.commit()
    
    return FileResponse.model_validate(file_model)


@router.post("/bulk-associate", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_associate_tag(
    request: BulkTagAssociateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Associate a tag with multiple files.
    
    Args:
        request: BulkTagAssociateRequest containing file_hashes, tag_name, and category
        db: Database session
    """
    if not request.file_hashes:
        return

    # Try to create the tag; if it exists, fetch it instead
    try:
        tag_category = TagCategory(request.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join([c.value for c in TagCategory])}"
        )
    
    tag = Tag(name=request.tag_name, category=tag_category)
    db.add(tag)
    
    try:
        await db.flush()  # Flush to get the tag ID
    except IntegrityError:
        # Tag already exists (unique constraint violation), fetch it
        await db.rollback()
        tag_result = await db.execute(
            select(Tag).where(Tag.name == request.tag_name).with_for_update()
        )
        tag = tag_result.scalar_one()
        
    # Find which files already have this tag to avoid duplicates
    existing_assocs = await db.execute(
        select(FileTag.file_sha256_hash)
        .where(
            FileTag.tag_id == tag.id,
            FileTag.file_sha256_hash.in_(request.file_hashes)
        ).with_for_update()
    )
    existing_hashes = set(existing_assocs.scalars().all())
    
    # Add associations for files that don't have the tag
    for file_hash in request.file_hashes:
        if file_hash not in existing_hashes:
            file_tag = FileTag(
                file_sha256_hash=file_hash,
                tag_id=tag.id
            )
            db.add(file_tag)
            
    try:
        await db.commit()
    except IntegrityError:
        # Race condition, someone else added it? 
        # TODO: Rollback and retry logic could be here, but for now just fail/rollback
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to associate tags due to concurrent modification"
        )


@router.delete("/dissociate", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def dissociate_tag(
    request: TagDissociateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Dissociate a tag from a file.
    
    Args:
        request: Request containing file_sha256 and tag_name
        db: Database session
        
    Returns:
        FileResponse with updated tags
    """
    # Verify file exists
    result = await db.execute(
        select(FileModel).where(FileModel.sha256_hash == request.file_sha256).with_for_update()
    )
    file_model = result.scalar_one_or_none()
    if file_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Find tag by name
    tag_result = await db.execute(
        select(Tag).where(Tag.name == request.tag_name).with_for_update()
    )
    tag = tag_result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Query and delete the FileTag association
    assoc_result = await db.execute(
        select(FileTag).where(
            FileTag.file_sha256_hash == request.file_sha256,
            FileTag.tag_id == tag.id
        ).with_for_update()
    )
    file_tag = assoc_result.scalar_one_or_none()
    
    if file_tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag association not found"
        )
    
    await db.delete(file_tag)
    await db.flush()
    
    # Reload file with tags
    result = await db.execute(
        select(FileModel)
        .options(selectinload(FileModel.tags))
        .where(FileModel.sha256_hash == request.file_sha256).with_for_update()  
    )
    file_model = result.scalar_one()
    
    await db.commit()
    
    return FileResponse.model_validate(file_model)


@router.post("/bulk-dissociate", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_dissociate_tag(
    request: BulkTagDissociateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Dissociate a tag from multiple files.
    
    Args:
        request: BulkTagDissociateRequest containing file_hashes and tag_name
        db: Database session
    """
    if not request.file_hashes:
        return

    # Find tag by name
    tag_result = await db.execute(
        select(Tag).where(Tag.name == request.tag_name).with_for_update()
    )
    tag = tag_result.scalar_one_or_none()
    if tag is None:
        # Tag doesn't exist, so it's not associated with any files
        return
    
    # Find and delete associations
    assoc_result = await db.execute(
        select(FileTag).where(
            FileTag.tag_id == tag.id,
            FileTag.file_sha256_hash.in_(request.file_hashes)
        ).with_for_update()
    )
    associations = assoc_result.scalars().all()
    
    for assoc in associations:
        await db.delete(assoc)
        
    await db.commit()
