"""Pool serializers for BijutsuBase API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, model_validator

from models.pool import PoolCategory
from api.serializers.file import FileThumb


class PoolSimple(BaseModel):
    """Simple pool response model."""
    id: uuid.UUID
    name: str
    member_count: int = 0
    thumbnail_url: Optional[str] = None


class CreatePoolRequest(BaseModel):
    """Request model for creating a new pool."""
    name: str
    description: Optional[str] = None
    category: PoolCategory = PoolCategory.SERIES


class UpdatePoolRequest(BaseModel):
    """Request model for updating a pool."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[PoolCategory] = None


class PoolMemberResponse(BaseModel):
    """Response model for a file within a pool."""
    file: FileThumb
    order: int
    added_at: datetime

    class Config:
        from_attributes = True


class PoolResponse(BaseModel):
    """Detailed pool response model."""
    id: uuid.UUID
    name: str
    description: Optional[str]
    category: PoolCategory
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    members: List[PoolMemberResponse] = []

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def compute_extras(cls, data: Any) -> Any:
        """Compute member_count from ORM object."""
        if hasattr(data, "members"):
             try:
                if not hasattr(data, "member_count") or data.member_count == 0:
                    data.member_count = len(data.members)
             except Exception:
                pass
                
        # Also sort members if they exist and are list
        if hasattr(data, "members") and isinstance(data.members, list):
             data.members = sorted(data.members, key=lambda x: x.order if hasattr(x, 'order') else 0)
             
        return data


class ReorderFilesRequest(BaseModel):
    """Request model for reordering files in a pool."""
    file_hashes: List[str]
    after_order: int

