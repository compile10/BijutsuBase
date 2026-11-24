"""API keys router for managing personal API keys on the current account."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.serializers.api_key import (
    ApiKeyListResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
)
from auth.api_keys import generate_api_key
from auth.users import current_active_user
from database.config import get_db
from models.api_key import ApiKey
from models.user import User

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> CreateApiKeyResponse:
    """Create a new API key for the currently authenticated account."""
    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        user_id=user.id,
        name=request.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        expires_at=request.expires_at,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return CreateApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        api_key=raw_key,
    )


@router.get("", response_model=ApiKeyListResponse, status_code=status.HTTP_200_OK)
async def list_api_keys(
    page: int = Query(1, ge=1, description="1-indexed page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of API keys per page"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> ApiKeyListResponse:
    """List API keys belonging to the currently authenticated account."""
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count(ApiKey.id)).where(ApiKey.user_id == user.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    api_keys = result.scalars().all()

    return ApiKeyListResponse(
        items=[ApiKeyResponse.model_validate(key) for key in api_keys],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> None:
    """Delete an API key belonging to the currently authenticated account."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == api_key_id,
            ApiKey.user_id == user.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()
