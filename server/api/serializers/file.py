"""File serializers for BijutsuBase API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, computed_field


class TagResponse(BaseModel):
    name: str
    category: str
    count: int

    class Config:
        from_attributes = True


class FileThumb(BaseModel):
    """Simplified file response model with only thumbnail URL and hash."""
    
    sha256_hash: str
    thumbnail_url: str
    
    class Config:
        from_attributes = True


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
    tags: list["TagResponse"]
    
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

