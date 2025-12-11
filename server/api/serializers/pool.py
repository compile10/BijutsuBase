"""Pool serializers for BijutsuBase API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, field_validator, model_validator

from models.pool import PoolCategory
from api.serializers.file import FileThumb
from utils.file_storage import generate_file_path


class PoolSimple(BaseModel):
    """Simple pool response model."""
    id: uuid.UUID
    name: str
    member_count: int = 0
    thumbnail_url: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @model_validator(mode='before')
    @classmethod
    def compute_extras(cls, data: Any) -> Any:
        """Compute member_count and thumbnail_url from ORM object."""
        # If data is an ORM object (has 'members' attribute)
        if hasattr(data, "members"):
            try:
                # Populate member_count
                if not hasattr(data, "member_count") or data.member_count == 0:
                    # We attach it to the object so Pydantic can read it
                    data.member_count = len(data.members)
                
                # Populate thumbnail_url if not present
                if not hasattr(data, "thumbnail_url") or data.thumbnail_url is None:
                    data.thumbnail_url = None
                    if data.members:
                        # Members are usually sorted by order, take the first one
                        first_member = data.members[0]
                        if hasattr(first_member, "file") and first_member.file:
                            path = generate_file_path(first_member.file.sha256_hash, "webp", thumb=True)
                            data.thumbnail_url = "/" + str(path).replace("\\", "/")
            except Exception:
                # Fallback if something fails during attribute access
                pass
                
        return data


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

