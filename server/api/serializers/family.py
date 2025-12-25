"""Family serializers for BijutsuBase API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, model_validator

from api.serializers.file import FileThumb

class FileFamilyResponse(BaseModel):
    """Detailed family response model."""
    id: uuid.UUID
    parent_sha256_hash: str
    parent: Optional[FileThumb] = None
    created_at: datetime
    updated_at: datetime
    children: List[FileThumb] = []
    
    class Config:
        from_attributes = True
    
    @model_validator(mode='before')
    @classmethod
    def extract_relationships(cls, data: Any) -> Any:
        """Extract parent and children from ORM object."""
        if hasattr(data, "parent"):
            # Extract parent file
            if data.parent:
                data.parent = FileThumb.model_validate(data.parent)
        
        if hasattr(data, "children"):
            # Extract children files
            if isinstance(data.children, list):
                data.children = [FileThumb.model_validate(child) for child in data.children]
        
        return data


class CreateFamilyRequest(BaseModel):
    """Request model for creating a new family."""
    parent_sha256_hash: str


class AddChildRequest(BaseModel):
    """Request model for adding a child to a family."""
    child_sha256_hash: str
