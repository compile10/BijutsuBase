"""File serializers for BijutsuBase API."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any

from pydantic import BaseModel, computed_field, field_validator, Field, model_validator
from sqlalchemy import inspect

from api.serializers.tag import TagResponse

if TYPE_CHECKING:
    from api.serializers.pool import PoolSimple


class FileThumb(BaseModel):
    """Simplified file response model with only thumbnail URL and hash."""
    
    sha256_hash: str
    processing_status: str = "completed"
    
    class Config:
        from_attributes = True

    @field_validator('processing_status', mode='before')
    @classmethod
    def convert_processing_status(cls, v: Any) -> str:
        """Convert enum to lowercase string value."""
        if v is None:
            return "completed"
        if hasattr(v, 'value'):
            return v.value  # Enum -> string value (lowercase)
        return str(v).lower()

    @computed_field
    @property
    def thumbnail_url(self) -> str | None:
        """
        Generate thumbnail URL using the file's hash.
        
        Returns None if processing is not completed (thumbnail not yet generated).
        """
        if self.processing_status != "completed":
            return None
            
        from utils.file_storage import generate_file_url
        
        # Thumbnails are always WebP format
        return generate_file_url(self.sha256_hash, "webp", thumb=True)


class FileResponse(BaseModel):
    """Response model for File objects."""
    
    sha256_hash: str
    md5_hash: str
    file_size: int
    original_filename: str
    file_ext: str
    file_type: str
    width: int | None
    height: int | None
    rating: str
    date_added: datetime
    source: str | None
    ai_generated: bool
    tag_source: str
    processing_status: str  # pending, processing, completed, failed
    processing_error: str | None = None  # Error message if processing failed
    tags: list["TagResponse"]
    pools: list["PoolSimple"] = Field(default=[], validation_alias="pool_entries")
    parent: Optional[FileThumb] = None  # Parent file thumbnail if this file is a child
    children: list[FileThumb] = Field(default_factory=list)  # Children file thumbnails if this file is a parent
    family_id: Optional[str] = None  # Family ID if this file is a parent of a family
    
    @field_validator('processing_status', mode='before')
    @classmethod
    def convert_processing_status(cls, v: Any) -> str:
        """Convert enum to lowercase string value."""
        if v is None:
            return "completed"
        if hasattr(v, 'value'):
            return v.value  # Enum -> string value (lowercase)
        return str(v).lower()
    
    @field_validator('tags')
    @classmethod
    def sort_tags(cls, tags: list["TagResponse"]) -> list["TagResponse"]:
        """Sort tags alphanumerically by name (natural sort)."""
        def natural_sort_key(tag: "TagResponse") -> list:
            """Convert tag name to a list of strings and integers for natural sorting."""
            return [int(text) if text.isdigit() else text.lower() 
                    for text in re.split(r'(\d+)', tag.name)]
        
        return sorted(tags, key=natural_sort_key)
    
    @field_validator('pools', mode='before')
    @classmethod
    def extract_pools(cls, v):
        """Extract pools from pool_entries relationship."""
        return [x.pool for x in v] if v and isinstance(v, list) and hasattr(v[0], 'pool') else (v or [])
    
    @model_validator(mode='before')
    @classmethod
    def extract_family_relationships(cls, data: Any) -> Any:
        """Extract parent, children, and family_id from family relationships."""
        parent = None
        children = []
        family_id = None
        
        # Assume `data` is a SQLAlchemy ORM `File`  instance.
        # (If it isn't, we want to fail loudly rather than silently returning empty family fields.)
        state = inspect(data)
        
        # Extract parent file if this file is a child in a family
        # Check if the relationship is loaded to avoid lazy loading
        if 'family_as_child' not in state.unloaded:
            family_as_child = data.family_as_child
            if family_as_child and family_as_child.parent:
                parent = FileThumb.model_validate(family_as_child.parent)
            # Set family_id for children too
            if family_as_child and hasattr(family_as_child, 'id'):
                family_id = str(family_as_child.id)
        
        # Extract children files if this file is a parent of a family
        # Check if the relationship is loaded to avoid lazy loading
        if 'family_as_parent' not in state.unloaded:
            family_as_parent = data.family_as_parent
            if family_as_parent:
                # Set family_id for parent
                if hasattr(family_as_parent, 'id'):
                    family_id = str(family_as_parent.id)
                child_files = getattr(family_as_parent, 'children', None)
                if child_files:
                    children = [FileThumb.model_validate(child) for child in child_files]
        
        # Set the extracted values on the ORM instance
        data.parent = parent
        data.children = children
        data.family_id = family_id
        
        return data
    
    @computed_field
    @property
    def thumbnail_url(self) -> str | None:
        """
        Generate thumbnail URL using the file's hash and extension.
        
        Returns None if processing is not completed (thumbnail not yet generated).
        
        Returns:
            URL path to the thumbnail (e.g., /media/thumb/9f/a3/9fa39b...webp) or None
        """
        from utils.file_storage import generate_file_url
        
        # Return None if file is still being processed (thumbnail not ready)
        if self.processing_status != "completed":
            return None
        
        # Thumbnails are always WebP format
        return generate_file_url(self.sha256_hash, "webp", thumb=True)
    
    @computed_field
    @property
    def original_url(self) -> str:
        """
        Generate original file URL using the file's hash and extension.
        
        Returns:
            URL path to the original file (e.g., /media/original/9f/a3/9fa39b...jpg)
        """
        from utils.file_storage import generate_file_url
        
        # Original file uses the file's actual extension
        return generate_file_url(self.sha256_hash, self.file_ext, thumb=False)
    
    class Config:
        from_attributes = True


class BulkFileRequest(BaseModel):
    """Request model for operations on multiple files."""
    file_hashes: list[str]


class BulkUpdateFileRequest(BaseModel):
    """Request model for bulk updating file metadata."""
    file_hashes: list[str]
    rating: Optional[str] = None
    ai_generated: Optional[bool] = None


class FileSearchResponse(BaseModel):
    """Response model for paginated file search."""
    items: list[FileThumb]
    next_cursor: Optional[str] = None
    has_more: bool

# Late import to avoid circular dependency issues at runtime
# This allows FileResponse to reference PoolSimple
from api.serializers.pool import PoolSimple
