"""File serializers for BijutsuBase API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
    date_added: datetime
    
    class Config:
        from_attributes = True

