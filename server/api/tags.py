"""Tags router for BijutsuBase API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import get_db
from models.file import File as FileModel
from models.tag import Tag, TagCategory, FileTag
from api.serializers.file import FileResponse


router = APIRouter(prefix="/tags", tags=["tags"])


class TagAssociateRequest(BaseModel):
    """Request model for associating a tag with a file."""
    
    file_sha256: str
    tag_name: str
    category: str


class TagDissociateRequest(BaseModel):
    """Request model for dissociating a tag from a file."""
    
    file_sha256: str
    tag_name: str


@router.post("/associate", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def associate_tag(
    request: TagAssociateRequest,
    db: AsyncSession = Depends(get_db),
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


@router.delete("/dissociate", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def dissociate_tag(
    request: TagDissociateRequest,
    db: AsyncSession = Depends(get_db),
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

