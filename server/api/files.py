"""File upload router for BijutsuBase API."""
from __future__ import annotations

import hashlib
import magic
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db
from models.file import File as FileModel
from utils.file_storage import generate_file_path
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
    original_filename = file.filename

    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename"
        )
    
    # Create temporary file for streaming in media directory (same filesystem as final location)
    temp_dir = Path("media/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir)
    temp_path = Path(temp_file.name)
    
    # Stream file content to temp location, validate type, and calculate hashes
    sha256_hasher = hashlib.sha256()
    md5_hasher = hashlib.md5()
    file_size = 0
    file_type = None
    
    # Read file in chunks
    chunk_size = 8192  # 8KB chunks
    first_chunk = True
    
    try:
        while chunk := await file.read(chunk_size):
            # Validate file type using first chunk
            if first_chunk:
                try:
                    file_type = magic.from_buffer(chunk, mime=True)
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
                first_chunk = False
            
            # Update hashes and write to temp file
            sha256_hasher.update(chunk)
            md5_hasher.update(chunk)
            temp_file.write(chunk)
            file_size += len(chunk)
    finally:
        await file.close()
        temp_file.close()
    
    # Get final hash digests
    sha256_hash = sha256_hasher.hexdigest()
    md5_hash = md5_hasher.hexdigest()
    
    # Check for duplicate
    result = await db.execute(
        select(FileModel).where(FileModel.sha256_hash == sha256_hash)
    )
    existing_file = result.scalar_one_or_none()
    if existing_file is not None:
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File with this hash already exists"
        )
    
    file_ext = Path(original_filename).suffix.lstrip(".")
    
    # Generate final file path and move temp file to final location
    final_path = generate_file_path(sha256_hash, file_ext)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.rename(final_path)
    
    # Create File model instance (dimensions will be extracted in event listener)
    file_model = FileModel(
        sha256_hash=sha256_hash,
        md5_hash=md5_hash,
        file_size=file_size,
        original_filename=original_filename,
        file_ext=file_ext,
        file_type=file_type
    )
    
    # Save to database
    try:
        db.add(file_model)
        await db.commit()
        await db.refresh(file_model)
    except Exception as e:
        await db.rollback()
        # Clean up the file if database commit fails
        final_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to database: {str(e)}"
        )
    
    # Return response
    return FileResponse.model_validate(file_model)

