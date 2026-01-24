"""Pools router for BijutsuBase API."""
from __future__ import annotations

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import get_db
from models.pool import Pool, PoolMember
from models.file import File
from models.user import User
from api.serializers.pool import (
    PoolResponse, 
    CreatePoolRequest, 
    UpdatePoolRequest, 
    PoolSimple,
    ReorderFilesRequest
)
from api.serializers.file import BulkFileRequest
from utils.file_storage import generate_file_path
from utils.rating import get_allowed_ratings
from auth.users import current_active_user

router = APIRouter(prefix="/pools", tags=["pools"])
logger = logging.getLogger(__name__)


def _normalize_pool_orders(members: list[PoolMember]) -> None:
    """Normalize pool member orders to be consecutive starting from 1.
    
    Sorts members by their current order and reassigns orders as 1, 2, 3, ...
    This ensures there are no gaps in the ordering.
    """
    sorted_members = sorted(members, key=lambda m: m.order)
    for i, member in enumerate(sorted_members, start=1):
        member.order = i


@router.get("/", response_model=List[PoolSimple], status_code=status.HTTP_200_OK)
async def list_pools(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    query: str | None = Query(None, description="Search query for pool name or description"),
    max_rating: str | None = Query(None, description="Maximum rating for thumbnail selection (safe, sensitive, questionable, explicit)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """List pools with pagination.
    
    The max_rating parameter only affects which thumbnail is shown for each pool.
    It does not filter the pools themselves or change the member count.
    """
    
    stmt = (
        select(Pool)
        .options(
            selectinload(Pool.members).selectinload(PoolMember.file)
        )
    )

    if query:
        search_filter = f"%{query}%"
        stmt = stmt.where(
            or_(
                Pool.name.ilike(search_filter),
                Pool.description.ilike(search_filter)
            )
        )

    stmt = (
        stmt
        .order_by(Pool.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    pools = result.scalars().all()
    
    # Get allowed ratings for thumbnail filtering
    allowed_ratings = get_allowed_ratings(max_rating) if max_rating else None
    
    # Build response with rating-filtered thumbnails
    response = []
    for pool in pools:
        # Find the first member with an allowed rating for thumbnail
        thumbnail_url = None
        sorted_members = sorted(pool.members, key=lambda m: m.order)
        for member in sorted_members:
            if member.file:
                # If no rating filter, use first member; otherwise check rating
                if allowed_ratings is None or member.file.rating in allowed_ratings:
                    path = generate_file_path(member.file.sha256_hash, "webp", thumb=True)
                    thumbnail_url = "/" + str(path).replace("\\", "/")
                    break
        
        response.append(PoolSimple(
            id=pool.id,
            name=pool.name,
            member_count=len(pool.members),
            thumbnail_url=thumbnail_url
        ))
    
    return response


@router.post("/", response_model=PoolResponse, status_code=status.HTTP_201_CREATED)
async def create_pool(
    request: CreatePoolRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Create a new pool."""
    pool = Pool(
        name=request.name,
        description=request.description,
        category=request.category
    )
    
    db.add(pool)
    await db.flush()
    await db.refresh(pool, attribute_names=["members"])
    await db.commit()
    
    response = PoolResponse.model_validate(pool)
    return response


@router.get("/{pool_id}", response_model=PoolResponse, status_code=status.HTTP_200_OK)
async def get_pool(
    pool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Get pool details by ID."""
    query = (
        select(Pool)
        .options(
            selectinload(Pool.members).selectinload(PoolMember.file)
        )
        .where(Pool.id == pool_id)
    )
    
    result = await db.execute(query)
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    
    response = PoolResponse.model_validate(pool)
    return response


@router.put("/{pool_id}", response_model=PoolResponse, status_code=status.HTTP_200_OK)
async def update_pool(
    pool_id: uuid.UUID,
    request: UpdatePoolRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Update pool metadata."""
    # Fetch pool with members to return full object
    query = (
        select(Pool)
        .options(
            selectinload(Pool.members).selectinload(PoolMember.file)
        )
        .where(Pool.id == pool_id)
        .with_for_update()
    )
    
    result = await db.execute(query)
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    
    if request.name is not None:
        pool.name = request.name
    if request.description is not None:
        pool.description = request.description
    if request.category is not None:
        pool.category = request.category
        
    await db.commit()
    await db.refresh(pool)
        
    response = PoolResponse.model_validate(pool)
    return response


@router.delete("/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pool(
    pool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Delete a pool."""
    query = select(Pool).where(Pool.id == pool_id)
    result = await db.execute(query)
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    
    await db.delete(pool)
    await db.commit()


@router.post("/{pool_id}/files", response_model=PoolResponse, status_code=status.HTTP_200_OK)
async def add_files_to_pool(
    pool_id: uuid.UUID,
    request: BulkFileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Add files to a pool."""
    if not request.file_hashes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")
        
    # Check if pool exists
    pool_query = (
        select(Pool)
        .options(selectinload(Pool.members))
        .where(Pool.id == pool_id).with_for_update()
    )
    result = await db.execute(pool_query)
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
        
    # Get current max order
    current_max_order = 0
    if pool.members:
        current_max_order = max(m.order for m in pool.members)
        
    # Filter out files that are already in the pool
    existing_hashes = {m.file_sha256_hash for m in pool.members}
    new_hashes = [h for h in request.file_hashes if h not in existing_hashes]
    
    if not new_hashes:
        # All files already in pool
        # Release lock since we aren't making changes
        await db.commit()
        
        # Re-fetch with file details for response
        response_query = (
            select(Pool)
            .options(selectinload(Pool.members).selectinload(PoolMember.file))
            .where(Pool.id == pool_id)
        )        
        result = await db.execute(response_query)
        pool = result.scalar_one_or_none()
        if pool is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
        response = PoolResponse.model_validate(pool)
        response.member_count = len(pool.members)
        return response

    # Verify files exist
    # if some files don't exist, we can proceed with the ones that do
    files_query = select(File.sha256_hash).where(File.sha256_hash.in_(new_hashes)).with_for_update()
    result = await db.execute(files_query)
    found_hashes = result.scalars().all()
            
    # Add new members
    for i, file_hash in enumerate(found_hashes):
        member = PoolMember(
            pool_id=pool_id,
            file_sha256_hash=file_hash,
            order=current_max_order + 1 + i
        )
        db.add(member)
        
    await db.commit()
    
    # Re-fetch complete pool data
    response_query = (
        select(Pool)
        .options(selectinload(Pool.members).selectinload(PoolMember.file))
        .where(Pool.id == pool_id)
    ) 
    result = await db.execute(response_query)
    pool = result.scalar_one_or_none()
    if pool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    
    response = PoolResponse.model_validate(pool)
    return response


@router.delete("/{pool_id}/files/{sha256}", response_model=PoolResponse, status_code=status.HTTP_200_OK)
async def remove_file_from_pool(
    pool_id: uuid.UUID,
    sha256: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Remove a file from a pool."""
    # Fetch pool with members using FOR UPDATE lock to safely delete and reorder
    pool_query = (
        select(Pool)
        .options(selectinload(Pool.members))
        .where(Pool.id == pool_id)
        .with_for_update()
    )
    result = await db.execute(pool_query)
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    
    # Find the member to remove
    member_to_remove = None
    for member in pool.members:
        if member.file_sha256_hash == sha256:
            member_to_remove = member
            break
    
    if not member_to_remove:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File is not in the pool")
        
    await db.delete(member_to_remove)
    await db.flush()
    
    # Normalize orders to eliminate gaps (refresh members list after delete)
    await db.refresh(pool, attribute_names=["members"])
    _normalize_pool_orders(pool.members)
    
    await db.commit()
    
    # Re-fetch complete pool data with file details for response
    response_query = (
        select(Pool)
        .options(selectinload(Pool.members).selectinload(PoolMember.file))
        .where(Pool.id == pool_id)
    )
    result = await db.execute(response_query)
    pool = result.scalar_one_or_none()

    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    response = PoolResponse.model_validate(pool)
    return response


@router.post("/{pool_id}/reorder", response_model=PoolResponse, status_code=status.HTTP_200_OK)
async def reorder_pool_files(
    pool_id: uuid.UUID,
    request: ReorderFilesRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Reorder files in a pool by moving specified files after a given position.
    
    Files in file_hashes will be placed starting at position after_order+1.
    Positions are always consecutive (1, 2, 3, ...) with no gaps.
    Use after_order=0 to move files to the beginning of the pool.
    """
    if not request.file_hashes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")
    
    # Fetch pool with members using FOR UPDATE lock
    pool_query = (
        select(Pool)
        .options(selectinload(Pool.members))
        .where(Pool.id == pool_id)
        .with_for_update()
    )
    result = await db.execute(pool_query)
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    
    # Validate all file_hashes exist in the pool
    member_map = {m.file_sha256_hash: m for m in pool.members}
    
    for file_hash in request.file_hashes:
        if file_hash not in member_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"File {file_hash} is not in the pool"
            )
    
    moving_hashes_set = set(request.file_hashes)
    
    # Get staying members sorted by current order
    staying_members = sorted(
        [m for m in pool.members if m.file_sha256_hash not in moving_hashes_set],
        key=lambda m: m.order
    )
    
    # Get moving members in the order specified by file_hashes
    moving_members = [member_map[h] for h in request.file_hashes]
    
    # Build the new sequence:
    # 1. Staying members at positions 1..after_order (first `after_order` staying members)
    # 2. Moving members
    # 3. Remaining staying members
    
    # Clamp after_order to valid range [0, len(staying_members)]
    insert_position = max(0, min(request.after_order, len(staying_members)))
    
    new_sequence = (
        staying_members[:insert_position] +
        moving_members +
        staying_members[insert_position:]
    )
    
    # Assign consecutive orders starting from 1
    for i, member in enumerate(new_sequence, start=1):
        member.order = i
    
    await db.commit()
    
    # Re-fetch complete pool data with file details
    response_query = (
        select(Pool)
        .options(selectinload(Pool.members).selectinload(PoolMember.file))
        .where(Pool.id == pool_id)
    )
    result = await db.execute(response_query)
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    
    response = PoolResponse.model_validate(pool)
    return response

