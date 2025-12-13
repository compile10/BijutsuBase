"""Explore router for BijutsuBase API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from database.config import get_db
from models.tag import Tag, TagCategory, FileTag
from models.file import File
from api.serializers.tag import CharacterResponse


router = APIRouter(prefix="/explore", tags=["explore"])


@router.get("/characters", response_model=list[CharacterResponse], status_code=200)
async def list_characters(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all character tags with pagination, sorted alphabetically.
    Each character includes an example thumbnail from the most recently added image.
    
    Args:
        skip: Number of items to skip for pagination
        limit: Maximum number of items to return (max 100)
        db: Database session
        
    Returns:
        List of CharacterResponse objects with name, count, and example thumbnail
    """
    file_tags_with_rn = (
        select(
            FileTag.tag_id,
            FileTag.file_sha256_hash,
            func.row_number()
            .over(
                partition_by=FileTag.tag_id,
                order_by=(File.date_added.desc(), File.sha256_hash.asc())
            )
            .label("rn")
        )
        .join(File, FileTag.file_sha256_hash == File.sha256_hash)
        .subquery()
    )
    
    # Filter to only get row_number = 1 (the latest file for each tag)
    # Note: We access the column as file_sha256_hash because we selected it from FileTag
    latest_file_filtered = (
        select(file_tags_with_rn.c.tag_id, file_tags_with_rn.c.file_sha256_hash)
        .where(file_tags_with_rn.c.rn == 1)
        .subquery()
    )
    
    latest_file = aliased(latest_file_filtered)
    
    # Main query: select character tags with their latest file hash
    stmt = (
        select(
            Tag.name,
            Tag.count,
            latest_file.c.file_sha256_hash.label("example_thumbnail")
        )
        .outerjoin(latest_file, Tag.id == latest_file.c.tag_id)
        .where(Tag.category == TagCategory.CHARACTER)
        .order_by(Tag.name.asc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    # Convert rows to CharacterResponse objects
    characters = [
        CharacterResponse(
            name=row.name,
            count=row.count,
            example_thumbnail=row.example_thumbnail
        )
        for row in rows
    ]
    
    return characters
