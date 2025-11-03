"""File serializers for BijutsuBase API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TagResponse(BaseModel):
    name: str
    category: str
    count: int

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
    
    class Config:
        from_attributes = True

