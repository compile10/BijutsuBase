"""Media serving router for BijutsuBase."""
from __future__ import annotations

import magic
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db
from models.file import File as FileModel


router = APIRouter()


@router.get("/original/{file_path:path}")
async def serve_media(
    file_path: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Serve media files from the media/original directory.
    
    Path traversal protection is enforced - requests outside the media/original directory
    will return 404.
    
    Args:
        file_path: Path to the file relative to the media/original directory
        db: Database session
        
    Returns:
        FileResponse with the requested media file
        
    Raises:
        HTTPException: 404 if file not found or path is invalid
    """
    # Get the absolute path of the media/original directory
    # This assumes the server is run from the server/ directory
    media_dir = Path("media").resolve()
    original_dir = media_dir / "original"
    
    # Construct the requested file path
    requested_path = (original_dir / file_path).resolve()
    
    # Security check: ensure the resolved path is within the media/original directory
    # This prevents directory traversal attacks (e.g., ../../../etc/passwd)
    try:
        requested_path.relative_to(original_dir)
    except ValueError:
        # Path is outside the media/original directory
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if file exists
    if not requested_path.exists() or not requested_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Try to get MIME type from database first (faster than reading file)
    mime_type = None
    filename = requested_path.name
    # Extract hash from filename (format: <64-char-hash>.<ext>)
    if '.' in filename:
        hash_part = filename.rsplit('.', 1)[0]
        if len(hash_part) == 64:
            # Query database for file record
            try:
                file_record = await db.scalar(
                    select(FileModel).where(FileModel.sha256_hash == hash_part)
                )
                if file_record:
                    mime_type = file_record.file_type
            except Exception:
                mime_type = None
    
    # Fallback to python-magic if not found in database
    if mime_type is None:
        try:
            mime_type = magic.from_file(str(requested_path), mime=True)
        except Exception:
            # Fallback to None if magic fails, FastAPI will infer from extension
            mime_type = None
    
    # Serve the file
    return FileResponse(
        path=str(requested_path),
        media_type=mime_type
    )


@router.get("/thumb/{file_path:path}")
async def serve_thumbnail(
    file_path: str,
    db: AsyncSession = Depends(get_db)
):
    # TODO: Consider adding a cache layer to serve thumbnails and original files
    # TODO: Consider adding a bulk thumbnail send endpoint
    """
    Serve thumbnail files from the media/thumb directory.
    
    Path traversal protection is enforced - requests outside the media/thumb directory
    will return 404.
    
    Args:
        file_path: Path to the file relative to the media/thumb directory
        db: Database session
        
    Returns:
        FileResponse with the requested thumbnail file (WebP format)
        
    Raises:
        HTTPException: 404 if file not found or path is invalid
    """
    # Get the absolute path of the media/thumb directory
    # This assumes the server is run from the server/ directory
    media_dir = Path("media").resolve()
    thumb_dir = media_dir / "thumb"
    
    # Construct the requested file path
    requested_path = (thumb_dir / file_path).resolve()
    
    # Security check: ensure the resolved path is within the media/thumb directory
    # This prevents directory traversal attacks (e.g., ../../../etc/passwd)
    try:
        requested_path.relative_to(thumb_dir)
    except ValueError:
        # Path is outside the media/thumb directory
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if file exists
    if not requested_path.exists() or not requested_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Thumbnails are always WebP format
    return FileResponse(
        path=str(requested_path),
        media_type="image/webp"
    )

