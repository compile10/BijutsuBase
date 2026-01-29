"""Background processing tasks for file uploads."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy import select

from database.config import AsyncSessionLocal
from models.file import File as FileModel, ProcessingStatus
from utils.file_storage import generate_file_path
from utils.thumbnail_gen import generate_video_thumbnail
from utils.file_info import get_video_dimensions
from sources.danbooru.enrich_file import enrich_file_with_danbooru
from sources.onnxmodel.enrich_file import enrich_file_with_onnx


logger = logging.getLogger(__name__)


async def _generate_video_thumbnail_for_file(file: FileModel) -> None:
    """
    Generate and save thumbnail for a video file.
    
    Args:
        file: The File model instance to generate thumbnail for
        
    Raises:
        RuntimeError: If thumbnail generation fails
    """
    file_path = generate_file_path(file.sha256_hash, file.file_ext)
    
    try:
        # Run thumbnail generation in thread pool to avoid blocking
        thumbnail_content = await asyncio.to_thread(generate_video_thumbnail, file_path)
    except Exception as e:
        raise RuntimeError(f"Failed to generate thumbnail: {str(e)}") from e
    
    # Generate thumbnail path (always WebP format)
    thumbnail_path = generate_file_path(file.sha256_hash, "webp", thumb=True)
    
    # Create parent directories if they don't exist
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write thumbnail to disk
    thumbnail_path.write_bytes(thumbnail_content)


async def _extract_video_dimensions(file: FileModel) -> tuple[Optional[int], Optional[int]]:
    """
    Extract width and height from a video file.
    
    Args:
        file: The File model instance
        
    Returns:
        Tuple of (width, height) or (None, None) on failure
    """
    file_path = generate_file_path(file.sha256_hash, file.file_ext)
    
    try:
        # Run dimension extraction in thread pool
        width, height = await asyncio.to_thread(get_video_dimensions, file_path)
        return width, height
    except Exception as e:
        logger.warning(f"Failed to extract video dimensions for {file.sha256_hash}: {e}")
        return None, None


async def process_file_background(sha256_hash: str) -> None:
    """
    Background task to process a file after upload.
    
    This function runs asynchronously after the upload endpoint returns.
    It handles:
    - Thumbnail generation for videos
    - Video dimension extraction
    - Danbooru/ONNX enrichment
    - Processing status updates
    
    Args:
        sha256_hash: The SHA256 hash of the file to process
    """
    logger.info(f"Starting background processing for {sha256_hash}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Load file (no need for relationships - enrichment handles tags internally)
            result = await db.execute(
                select(FileModel).where(FileModel.sha256_hash == sha256_hash)
            )
            file = result.scalar_one_or_none()
            
            if file is None:
                logger.error(f"File not found for background processing: {sha256_hash}")
                return
            
            # Update status to processing
            file.processing_status = ProcessingStatus.PROCESSING
            await db.commit()
            
            # Process based on file type
            file_type = file.file_type or ""
            
            if file_type.startswith("video/"):
                # Extract dimensions if not already done
                if file.width is None or file.height is None:
                    logger.info(f"Extracting video dimensions for {sha256_hash}")
                    width, height = await _extract_video_dimensions(file)
                    file.width = width
                    file.height = height
                
                # Generate thumbnail
                logger.info(f"Generating video thumbnail for {sha256_hash}")
                await _generate_video_thumbnail_for_file(file)
            
            # Run enrichment (Danbooru first, fallback to ONNX)
            logger.info(f"Running enrichment for {sha256_hash}")
            try:
                danbooru_success = await enrich_file_with_danbooru(file, db)
                if not danbooru_success:
                    logger.info(f"Danbooru lookup failed for {sha256_hash}, falling back to ONNX")
                    try:
                        await enrich_file_with_onnx(file, db)
                    except Exception as e:
                        logger.warning(f"ONNX enrichment failed for {sha256_hash}: {e}")
            except Exception as e:
                logger.warning(f"Enrichment failed for {sha256_hash}: {e}")
            
            # Mark as completed
            file.processing_status = ProcessingStatus.COMPLETED
            file.processing_error = None
            await db.commit()
            
            logger.info(f"Background processing completed for {sha256_hash}")
            
        except Exception as e:
            logger.exception(f"Background processing failed for {sha256_hash}")
            
            # Try to mark as failed
            try:
                await db.rollback()
                
                # Re-fetch the file to update status
                result = await db.execute(
                    select(FileModel).where(FileModel.sha256_hash == sha256_hash)
                )
                file = result.scalar_one_or_none()
                
                if file:
                    file.processing_status = ProcessingStatus.FAILED
                    file.processing_error = str(e)[:2000]  # Truncate to fit column
                    await db.commit()
            except Exception as inner_e:
                logger.exception(f"Failed to update processing status for {sha256_hash}: {inner_e}")
