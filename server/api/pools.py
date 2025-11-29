"""Pools router for BijutsuBase API."""
from __future__ import annotations

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import get_db
from models.pool import Pool, PoolMember
from models.file import File
from api.serializers.pool import (
    PoolResponse, 
    CreatePoolRequest, 
    UpdatePoolRequest, 
    PoolSimple
)
from api.serializers.file import BulkFileRequest
from utils.file_storage import generate_file_path

router = APIRouter(prefix="/pools", tags=["pools"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[PoolSimple], status_code=status.HTTP_200_OK)
async def list_pools(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List pools with pagination."""
    
    query = (
        select(Pool)
        .options(
            selectinload(Pool.members).selectinload(PoolMember.file)
        )
        .order_by(Pool.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    pools = result.scalars().all()
    
    return [PoolSimple.model_validate(pool) for pool in pools]


@router.post("/", response_model=PoolResponse, status_code=status.HTTP_201_CREATED)
async def create_pool(
    request: CreatePoolRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new pool."""
    pool = Pool(
        name=request.name,
        description=request.description,
        category=request.category
    )
    
    db.add(pool)
    await db.commit()
    await db.refresh(pool)
    
    response = PoolResponse.model_validate(pool)
    return response


@router.get("/{pool_id}", response_model=PoolResponse, status_code=status.HTTP_200_OK)
async def get_pool(
    pool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
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

        if not response_query:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
        
        result = await db.execute(response_query)
        pool = result.scalar_one()
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
    if not response_query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
        
    result = await db.execute(response_query)
    pool = result.scalar_one()
    
    response = PoolResponse.model_validate(pool)
    return response


@router.delete("/{pool_id}/files/{sha256}", response_model=PoolResponse, status_code=status.HTTP_200_OK)
async def remove_file_from_pool(
    pool_id: uuid.UUID,
    sha256: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a file from a pool."""
    # Check if member exists
    query = select(PoolMember).where(
        PoolMember.pool_id == pool_id,
        PoolMember.file_sha256_hash == sha256
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File is not in the pool")
        
    await db.delete(member)
    await db.commit()
    
    # Re-fetch complete pool data
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

