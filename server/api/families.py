"""Families router for BijutsuBase API."""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import get_db
from models.family import FileFamily
from models.file import File
from api.serializers.family import (
    FileFamilyResponse,
    CreateFamilyRequest,
    AddChildRequest
)
from api.serializers.file import FileThumb

router = APIRouter(prefix="/families", tags=["families"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=FileFamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_family(
    request: CreateFamilyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new family with a parent file."""
    # Check if parent file exists
    parent_query = select(File).where(File.sha256_hash == request.parent_sha256_hash)
    result = await db.execute(parent_query)
    parent_file = result.scalar_one_or_none()
    
    if not parent_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent file not found"
        )
    
    # Check if parent file is already a parent of another family
    existing_family_query = select(FileFamily).where(
        FileFamily.parent_sha256_hash == request.parent_sha256_hash
    )
    result = await db.execute(existing_family_query)
    existing_family = result.scalar_one_or_none()
    
    if existing_family:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is already a parent of a family"
        )
    
    # Check if parent file is already a child in another family
    if parent_file.parent_family_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is already a child in another family"
        )
    
    # Create the family
    family = FileFamily(parent_sha256_hash=request.parent_sha256_hash)
    
    db.add(family)
    await db.commit()
    await db.refresh(family)

    return FileFamilyResponse(
        id=family.id,
        parent_sha256_hash=family.parent_sha256_hash,
        parent=FileThumb.model_validate(parent_file),
        children=[],
        created_at=family.created_at,
        updated_at=family.updated_at,
    )


@router.get("/{family_id}", response_model=FileFamilyResponse, status_code=status.HTTP_200_OK)
async def get_family(
    family_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get family details by ID."""
    query = (
        select(FileFamily)
        .options(
            selectinload(FileFamily.parent),
            selectinload(FileFamily.children)
        )
        .where(FileFamily.id == family_id)
    )
    
    result = await db.execute(query)
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found"
        )
    
    return FileFamilyResponse.model_validate(family)


@router.post("/{family_id}/children", response_model=FileFamilyResponse, status_code=status.HTTP_200_OK)
async def add_child_to_family(
    family_id: uuid.UUID,
    request: AddChildRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a child file to a family."""
    # Check if family exists
    family_query = (
        select(FileFamily)
        .where(FileFamily.id == family_id)
        .with_for_update()
    )
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found"
        )
    
    # Check if child file exists
    child_query = select(File).where(File.sha256_hash == request.child_sha256_hash).with_for_update()
    result = await db.execute(child_query)
    child_file = result.scalar_one_or_none()
    
    if not child_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child file not found"
        )
    
    # Check if child is already in a family
    if child_file.parent_family_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is already a child in another family"
        )
    
    # Check if child is the parent of this family
    if child_file.sha256_hash == family.parent_sha256_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add parent file as its own child"
        )
    
    # Check if child is a parent of another family
    existing_parent_family_query = select(FileFamily).where(
        FileFamily.parent_sha256_hash == request.child_sha256_hash
    )
    result = await db.execute(existing_parent_family_query)
    existing_parent_family = result.scalar_one_or_none()
    
    if existing_parent_family:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is already a parent of another family"
        )
    
    # Add child to family
    child_file.parent_family_id = family_id
    await db.commit()

    # Load relationships for response (avoid async lazy-load during serialization)
    await db.refresh(family, attribute_names=["parent", "children"])
    
    return FileFamilyResponse.model_validate(family)


@router.delete("/{family_id}/children/{sha256}", response_model=FileFamilyResponse, status_code=status.HTTP_200_OK)
async def remove_child_from_family(
    family_id: uuid.UUID,
    sha256: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a child file from a family."""
    # Check if family exists
    family_query = (
        select(FileFamily)
        .where(FileFamily.id == family_id)
        .with_for_update()
    )
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found"
        )
    
    # Check if child file exists and is in this family
    child_query = (
        select(File)
        .where(
            File.sha256_hash == sha256,
            File.parent_family_id == family_id
        )
        .with_for_update()
    )
    result = await db.execute(child_query)
    child_file = result.scalar_one_or_none()
    
    if not child_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File is not a child in this family"
        )
    
    # Remove child from family
    child_file.parent_family_id = None
    await db.commit()

    await db.refresh(family, attribute_names=["parent", "children"])
    
    return FileFamilyResponse.model_validate(family)


@router.delete("/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family(
    family_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a family (unlinks children, doesn't delete files)."""
    # Check if family exists
    family_query = (
        select(FileFamily)
        .where(FileFamily.id == family_id)
        .with_for_update()
    )
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()
    
    
    # Delete the family
    await db.delete(family)
    await db.commit()
