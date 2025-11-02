"""File upload router for BijutsuBase API."""
from __future__ import annotations

import hashlib
import magic
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db
from models.file import File as FileModel
from utils.file_info import get_image_dimensions, get_video_dimensions
from api.serializers.file import FileResponse


router = APIRouter(prefix="/files", tags=["files"])


@router.put("/upload", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a file (image or video) to BijutsuBase.
    
    Validates file type, calculates hashes, extracts metadata,
    and stores the file in the database and on disk.
    """

    # TODO: Convert to a streaming upload model with chunked reading for large files.
    # We would need to save the file to disk in chunks and THEN handle database ops.

    # Read file content into memory
    content = await file.read()
    original_filename = file.filename

    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename"
        )
    
    # Validate file type using python-magic
    try:
        file_type = magic.from_buffer(content, mime=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine file type"
        )
    
    if not (file_type.startswith("image/") or file_type.startswith("video/")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image or video"
        )
    
    # Calculate hashes
    sha256_hash = hashlib.sha256(content).hexdigest()
    md5_hash = hashlib.md5(content).hexdigest()
    
    # Check for duplicate
    result = await db.execute(
        select(FileModel).where(FileModel.sha256_hash == sha256_hash)
    )
    existing_file = result.scalar_one_or_none()
    if existing_file is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File with this hash already exists"
        )
    
    # Extract metadata
    file_size = len(content)
    file_ext = Path(original_filename).suffix.lstrip(".")
    
    # Get dimensions
    width = None
    height = None
    try:
        if file_type.startswith("image/"):
            width, height = get_image_dimensions(content)
        elif file_type.startswith("video/"):
            width, height = get_video_dimensions(content)
    except (IOError, ValueError):
        # If dimension extraction fails, fail with 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract file dimensions"
        )
    
    # Create File model instance
    file_model = FileModel(
        sha256_hash=sha256_hash,
        md5_hash=md5_hash,
        file_size=file_size,
        original_filename=original_filename,
        file_ext=file_ext,
        file_type=file_type,
        width=width,
        height=height
    )
    
    # Store content in File
    file_model.set_temp_file_content(content)
    
    # Save to database
    try:
        db.add(file_model)
        await db.commit()
        await db.refresh(file_model)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to database: {str(e)}"
        )
    
    # Return response
    return FileResponse.model_validate(file_model)

