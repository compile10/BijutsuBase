"""File upload router for BijutsuBase API."""
from __future__ import annotations

import hashlib
import magic
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import get_db
from models.file import File as FileModel
from utils.file_storage import generate_file_path
from api.serializers.file import FileResponse
from tagging.danbooru.file import make_danbooru_request


router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{sha256}", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def get_file(
    sha256: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a file by its SHA-256 hash and return serialized details including tags."""
    result = await db.execute(
        select(FileModel).options(selectinload(FileModel.tags)).where(FileModel.sha256_hash == sha256)
    )
    file_model = result.scalar_one_or_none()
    if file_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse.model_validate(file_model)


@router.delete("/{sha256}", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def delete_file(
    sha256: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a file by its SHA-256 hash and return its details prior to deletion."""
    # Load file with tags for serialization and to ensure relationships are present
    result = await db.execute(
        select(FileModel).options(selectinload(FileModel.tags)).where(FileModel.sha256_hash == sha256)
    )
    file_model = result.scalar_one_or_none()
    if file_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Serialize before deletion to return details after deletion
    response = FileResponse.model_validate(file_model)

    try:
        # Delete association rows via ORM to trigger tag count decrements
        from models.tag import FileTag

        assoc_result = await db.execute(
            select(FileTag).where(FileTag.file_sha256_hash == sha256)
        )
        associations = assoc_result.scalars().all()
        for assoc in associations:
            await db.delete(assoc)
        await db.flush()

        # Delete the file record; after_delete hook removes files from disk
        await db.delete(file_model)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete file: {str(e)}")

    return response


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
    
    # Extract dimensions from the file
    width = None
    height = None
    try:
        if file_type.startswith("image/"):
            from utils.file_info import get_image_dimensions
            width, height = get_image_dimensions(final_path)
        elif file_type.startswith("video/"):
            from utils.file_info import get_video_dimensions
            width, height = get_video_dimensions(final_path)
    except Exception as e:
        # Clean up the file if dimension extraction fails
        final_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract dimensions: {str(e)}"
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
    
    # Save to database
    try:
        db.add(file_model)
        await db.flush()  # Flush to ensure file is in session before adding tags
        
        # Enrich file with Danbooru metadata (requires file to be in session for tags)
        await make_danbooru_request(db, file_model)
        
        await db.commit()
        await db.refresh(file_model)
        # Load tags relationship to include in response
        await db.refresh(file_model, attribute_names=["tags"])
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

