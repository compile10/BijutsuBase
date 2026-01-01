"""File serializers for BijutsuBase API."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any

from pydantic import BaseModel, computed_field, field_validator, Field, model_validator

from api.serializers.tag import TagResponse

if TYPE_CHECKING:
    from api.serializers.pool import PoolSimple


class FileThumb(BaseModel):
    """Simplified file response model with only thumbnail URL and hash."""
    
    sha256_hash: str
    
    class Config:
        from_attributes = True

    @computed_field
    @property
    def thumbnail_url(self) -> str:
        """
        Generate thumbnail URL using the file's hash.
        """
        from utils.file_storage import generate_file_path
        
        # Thumbnails are always WebP format
        thumbnail_path = generate_file_path(self.sha256_hash, "webp", thumb=True)
        
        return "/" + str(thumbnail_path).replace("\\", "/")


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
    tags: list["TagResponse"]
    pools: list["PoolSimple"] = Field(default=[], validation_alias="pool_entries")
    parent: Optional[FileThumb] = None  # Parent file thumbnail if this file is a child
    children: list[FileThumb] = Field(default_factory=list)  # Children file thumbnails if this file is a parent
    family_id: Optional[uuid.UUID] = None  # Family ID if this file is in/owns a family (supports empty families)
    
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
        """Extract parent and children FileThumb objects from family relationships."""
        parent = None
        children = []
        family_id = None
        
        # Extract parent file if this file is a child in a family
        if hasattr(data, 'family_as_child') and data.family_as_child:
            # This file is a child, so get the parent File object
            if hasattr(data.family_as_child, 'parent') and data.family_as_child.parent:
                parent = FileThumb.model_validate(data.family_as_child.parent)
            # This file is a child, so family id is stored on the file row
            if hasattr(data, 'parent_family_id'):
                family_id = data.parent_family_id
        
        # Extract children files if this file is a parent of a family
        if hasattr(data, 'family_as_parent') and data.family_as_parent:
            # This file is a parent, so get all children File objects
            if hasattr(data.family_as_parent, 'children') and data.family_as_parent.children:
                children = [FileThumb.model_validate(child) for child in data.family_as_parent.children]
            # This file is a parent, so family id is the family row id
            if hasattr(data.family_as_parent, 'id'):
                family_id = data.family_as_parent.id
        
        # Set the extracted values
        if isinstance(data, dict):
            data['parent'] = parent
            data['children'] = children
            data['family_id'] = family_id
        else:
            data.parent = parent
            data.children = children
            data.family_id = family_id
        
        return data
    
    @computed_field
    @property
    def thumbnail_url(self) -> str:
        """
        Generate thumbnail URL using the file's hash and extension.
        
        Returns:
            URL path to the thumbnail (e.g., /media/thumb/9f/a3/9fa39b...webp)
        """
        from utils.file_storage import generate_file_path
        
        # Thumbnails are always WebP format
        thumbnail_path = generate_file_path(self.sha256_hash, "webp", thumb=True)
        
        # Convert Path to URL path
        # generate_file_path returns: media/thumb/<first_two>/<next_two>/<hash>.webp
        # We want: /media/thumb/<first_two>/<next_two>/<hash>.webp
        return "/" + str(thumbnail_path).replace("\\", "/")
    
    @computed_field
    @property
    def original_url(self) -> str:
        """
        Generate original file URL using the file's hash and extension.
        
        Returns:
            URL path to the original file (e.g., /media/original/9f/a3/9fa39b...jpg)
        """
        from utils.file_storage import generate_file_path
        
        # Original file uses the file's actual extension
        original_path = generate_file_path(self.sha256_hash, self.file_ext, thumb=False)
        
        # Convert Path to URL path
        # generate_file_path returns: media/original/<first_two>/<next_two>/<hash>.<ext>
        # We want: /media/original/<first_two>/<next_two>/<hash>.<ext>
        return "/" + str(original_path).replace("\\", "/")
    
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
