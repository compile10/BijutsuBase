"""Files router for BijutsuBase API."""
from __future__ import annotations

from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import get_db
from models.file import File as FileModel, Rating
from models.tag import Tag, FileTag
from utils.file_storage import generate_file_path
from api.serializers.file import FileResponse, FileThumb, BulkFileRequest, BulkUpdateFileRequest
from api.serializers.tag import TagResponse


router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)


class FileRatingUpdate(BaseModel):
    """Request model for updating file rating."""
    rating: str


class FileAiGeneratedUpdate(BaseModel):
    """Request model for updating file ai_generated status."""
    ai_generated: bool


@router.get("/search", response_model=list[FileThumb], status_code=status.HTTP_200_OK)
async def search_files(
    tags: str = Query("", description="Space-separated list of tag names"),
    sort: str = Query("date_desc", description="Sort order: date_desc, date_asc, size_desc, size_asc"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for files that contain ALL of the specified tags.
    
    Args:
        tags: Space-separated list of tag names to search for
        sort: Sort order (date_desc, date_asc, size_desc, size_asc)
        db: Database session
        
    Returns:
        List of FileThumb objects containing sha256_hash and thumbnail_url for matching files
    """
    # Split space-separated tag names and filter out empty strings
    tag_names = [tag.strip() for tag in tags.split() if tag.strip()]
    
    # Determine sort order
    sort_column = None
    if sort == "date_desc":
        sort_column = FileModel.date_added.desc()
    elif sort == "date_asc":
        sort_column = FileModel.date_added.asc()
    elif sort == "size_desc":
        sort_column = FileModel.file_size.desc()
    elif sort == "size_asc":
        sort_column = FileModel.file_size.asc()
    else:
        # Default to date_desc if invalid sort param provided
        sort_column = FileModel.date_added.desc()

    if tag_names:
        # Query files that have ALL of the specified tags
        # We join File -> FileTag -> Tag, filter by tag names, group by file,
        # and ensure the count of distinct tags matches the number of requested tags
        query = (
            select(FileModel.sha256_hash)
            .join(FileTag, FileModel.sha256_hash == FileTag.file_sha256_hash)
            .join(Tag, FileTag.tag_id == Tag.id)
            .where(Tag.name.in_(tag_names))
            .group_by(FileModel.sha256_hash)
            .having(func.count(func.distinct(Tag.id)) == len(tag_names))
            .order_by(sort_column)
        )
    else:
        # If no tags provided, return all files
        query = select(FileModel.sha256_hash).order_by(sort_column)
    
    result = await db.execute(query)
    file_hashes = result.scalars().all()
    
    # Convert to FileThumb objects
    # generate_file_path returns "media/thumb/ab/cd/hash.webp"
    # Prepend "/" to make it a URL path: "/media/thumb/ab/cd/hash.webp"
    # TODO: Cleanup to match other file responses
    file_thumbs = [
        FileThumb(
            sha256_hash=sha256_hash,
            thumbnail_url="/" + str(generate_file_path(sha256_hash, "webp", thumb=True)).replace("\\", "/")
        )
        for sha256_hash in file_hashes
    ]
    
    return file_thumbs


@router.post("/bulk-common-tags", response_model=list[TagResponse], status_code=status.HTTP_200_OK)
async def get_common_tags(
    request: BulkFileRequest,
    db: AsyncSession = Depends(get_db),
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
):
    """Fetch a file by its SHA-256 hash and return serialized details including tags."""
    result = await db.execute(
        select(FileModel).options(selectinload(FileModel.tags)).where(FileModel.sha256_hash == sha256)
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
        
        # Load tags for response (still within same transaction)
        await db.refresh(file_model, ["tags"])
        await db.commit()
        
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
        
        # Load tags for response (still within same transaction)
        await db.refresh(file_model, ["tags"])
        await db.commit()
        
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


@router.delete("/{sha256}", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def delete_file(
    sha256: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a file by its SHA-256 hash and return its details prior to deletion."""
    # Load file with tags for serialization and to ensure relationships are present
    result = await db.execute(
        select(FileModel).options(selectinload(FileModel.tags)).where(FileModel.sha256_hash == sha256)
    )
    file_model = result.scalar_one_or_none()
    if file_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Serialize before deletion to return details after deletion
    response = FileResponse.model_validate(file_model)

    try:
        # Delete association rows via ORM to trigger tag count decrements
        from models.tag import FileTag

        assoc_result = await db.execute(
            select(FileTag).where(FileTag.file_sha256_hash == sha256)
        )
        associations = assoc_result.scalars().all()
        for assoc in associations:
            await db.delete(assoc)

        # refresh the file model to get the latest tags
        await db.refresh(file_model, ["tags"])

        # Delete the file record; after_delete hook removes files from disk
        await db.delete(file_model)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete file: {str(e)}")

    return response
