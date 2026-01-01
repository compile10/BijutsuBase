"""Family serializers for BijutsuBase API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from api.serializers.file import FileThumb

class FileFamilyResponse(BaseModel):
    """Detailed family response model."""
    id: uuid.UUID
    parent_sha256_hash: str
    parent: Optional[FileThumb] = None
    created_at: datetime
    updated_at: datetime
    children: List[FileThumb] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class CreateFamilyRequest(BaseModel):
    """Request model for creating a new family."""
    parent_sha256_hash: str


class AddChildRequest(BaseModel):
    """Request model for adding a child to a family."""
    child_sha256_hash: str
