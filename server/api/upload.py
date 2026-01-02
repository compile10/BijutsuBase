"""Upload router for BijutsuBase API."""
from __future__ import annotations

import hashlib
import magic
import tempfile
from pathlib import Path
from typing import Optional, AsyncIterator
import mimetypes
import httpx
from urllib.parse import urlparse

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.config import get_db
from api.serializers.file import FileResponse
from utils.file_storage import generate_file_path
from sources.danbooru.enrich_file import enrich_file_with_danbooru
from sources.onnxmodel.enrich_file import enrich_file_with_onnx
from models.file import File as FileModel
from models.pool import PoolMember, Pool
import logging


router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)

async def _stream_to_temp_and_hash(
    chunk_iter: AsyncIterator[bytes],
) -> tuple[Path, str, str, int, str]:
    """
    Stream chunks to a temp file, detect mime on first chunk, validate media type,
    and compute sha256/md5 hashes and total size.
    Returns: (temp_path, sha256_hash, md5_hash, file_size, mime_type)
    """
    temp_dir = Path("media/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir)
    temp_path = Path(temp_file.name)

    sha256_hasher = hashlib.sha256()
    md5_hasher = hashlib.md5()
    file_size = 0
    mime_type: Optional[str] = None
    first_chunk = True

    try:
        async for chunk in chunk_iter:
            if not chunk:
                continue
            if first_chunk:
                try:
                    mime_type = magic.from_buffer(chunk, mime=True)
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unable to determine file type",
                    )
                if not (mime_type.startswith("image/") or mime_type.startswith("video/")):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File must be an image or video",
                    )
                first_chunk = False
            sha256_hasher.update(chunk)
            md5_hasher.update(chunk)
            temp_file.write(chunk)
            file_size += len(chunk)
    except HTTPException:
        temp_file.close()
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        temp_file.close()
        temp_path.unlink(missing_ok=True)
        logger.exception("Error writing to temp file during stream")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write to temp file: {str(e)}",
        )
    finally:
        try:
            temp_file.close()
        except Exception:
            pass

    if mime_type is None:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine file type",
        )

    return (
        temp_path,
        sha256_hasher.hexdigest(),
        md5_hasher.hexdigest(),
        file_size,
        mime_type,
    )

async def _persist_ingest(
    temp_path: Path,
    sha256_hash: str,
    md5_hash: str,
    file_size: int,
    original_filename: str,
    mime_type: str,
    db: AsyncSession,
) -> FileResponse:
    """
    Finalize an ingest after a file has been streamed to a temp path.
    Handles duplicate check, file move, dimension extraction, DB save and enrichment.
    """
    # Duplicate check
    try:
        existing = await db.scalar(
            select(FileModel).where(FileModel.sha256_hash == sha256_hash)
        )
        if existing is not None:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="File with this hash already exists",
            )
    except HTTPException:
        # pass-through expected error
        raise
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        logger.exception("Database error while checking for duplicate file")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check for existing file: {str(e)}",
        )

    # Determine extension
    def _ext_from_mime(mime: str) -> Optional[str]:
        common_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/heic": "heic",
            "image/heif": "heif",
            "video/mp4": "mp4",
            "video/webm": "webm",
            "video/x-matroska": "mkv",
            "video/quicktime": "mov",
            "video/x-msvideo": "avi",
            "video/mpeg": "mpg",
        }
        if mime in common_map:
            return common_map[mime]
        guess = mimetypes.guess_extension(mime)
        if guess:
            return guess.lstrip(".")
        # final fallback
        if "/" in mime:
            subtype = mime.split("/", 1)[1]
            if "+" in subtype:
                subtype = subtype.split("+", 1)[0]
            return subtype
        return None

    file_ext = Path(original_filename).suffix.lstrip(".")
    if not file_ext:
        file_ext = _ext_from_mime(mime_type) or "bin"

    # Move to final location
    final_path = generate_file_path(sha256_hash, file_ext)
    try:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.rename(final_path)
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to move file to final location: {str(e)}",
        )

    # Extract dimensions
    width = None
    height = None
    ai_generated = False
    phash = None
    try:
        if mime_type.startswith("image/"):
            from utils.file_info import get_image_dimensions, is_ai_generated_image
            from utils.phash import compute_phash
            
            width, height = get_image_dimensions(final_path)
            
            # Detect AI-generated via EXIF UserComment
            try:
                ai_generated = is_ai_generated_image(final_path)
            except Exception:
                ai_generated = False
            
            # Compute perceptual hash for visual similarity detection
            try:
                phash = compute_phash(final_path)
                logger.debug(f"Computed pHash {phash} for {sha256_hash}")
            except Exception as e:
                logger.warning(f"Failed to compute pHash for {sha256_hash}: {str(e)}")
                # Continue without pHash - it's optional
        
        elif mime_type.startswith("video/"):
            from utils.file_info import get_video_dimensions
            width, height = get_video_dimensions(final_path)
    except Exception as e:
        final_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract dimensions: {str(e)}",
        )

    # Persist to DB and enrich
    file_model = FileModel(
        sha256_hash=sha256_hash,
        md5_hash=md5_hash,
        file_size=file_size,
        original_filename=original_filename,
        file_ext=file_ext,
        file_type=mime_type,
        width=width,
        height=height,
        ai_generated=ai_generated,
        phash=phash,
    )

    try:
        db.add(file_model)
        await db.flush()
    except IntegrityError:
        # Another transaction inserted the same sha256_hash concurrently.
        # Do NOT delete final_path; it's the canonical location for this hash.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File with this hash already exists",
        )
    except Exception as e:
        await db.rollback()
        # Cleanup disk if DB fails for other reasons
        final_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to database: {str(e)}",
        )

    try:
        danbooru_success = await enrich_file_with_danbooru(file_model, db)
        if not danbooru_success:
            try:
                await enrich_file_with_onnx(file_model, db)
            except Exception as e:
                logger.warning("All tagging failed for %s: %s", file_model.sha256_hash, str(e))
        
        # Flush to write tags to database
        await db.flush()
        
        # Now commit everything together
        await db.commit()

        # Reload file with all relationships needed for response
        # We need to reload after commit because commit expires the instance
        # and we need to eager load relationships to avoid MissingGreenlet error
        result = await db.execute(
            select(FileModel)
            .options(
                selectinload(FileModel.tags),
                selectinload(FileModel.pool_entries)
                .selectinload(PoolMember.pool)
                .selectinload(Pool.members)
                .selectinload(PoolMember.file)
            )
            .where(FileModel.sha256_hash == sha256_hash)
        )
        file_model = result.scalar_one()
        
        # Check for visually similar files and create/extend families
        if phash is not None:
            try:
                from utils.phash import find_similar_files
                from utils.similarity_family import handle_similar_files
                
                logger.debug(f"Searching for visually similar files to {sha256_hash}")
                similar_files = await find_similar_files(
                    phash=phash,
                    db=db,
                    exclude_hash=sha256_hash
                )
                
                if similar_files:
                    logger.info(f"Found {len(similar_files)} visually similar files for {sha256_hash}")
                    await handle_similar_files(file_model, similar_files, db)
                    
                    # Reload file with updated family relationships
                    from models.family import FileFamily
                    result = await db.execute(
                        select(FileModel)
                        .options(
                            selectinload(FileModel.tags),
                            selectinload(FileModel.pool_entries)
                            .selectinload(PoolMember.pool)
                            .selectinload(Pool.members)
                            .selectinload(PoolMember.file),
                            selectinload(FileModel.family_as_child).selectinload(FileFamily.parent),
                            selectinload(FileModel.family_as_parent).selectinload(FileFamily.children)
                        )
                        .where(FileModel.sha256_hash == sha256_hash)
                    )
                    file_model = result.scalar_one()
            except Exception as e:
                logger.error(f"Failed to process visual similarity for {sha256_hash}: {str(e)}", exc_info=True)
                # Don't fail the upload if similarity detection fails

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enrich file with metadata: {str(e)}",
        )

    return FileResponse.model_validate(file_model)

class UrlUploadRequest(BaseModel):
    url: HttpUrl


@router.post("/url", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def upload_url(
    payload: UrlUploadRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file by URL. Downloads to a temp file, validates type, hashes content,
    then reuses the ingest finalization flow.
    """
    chunk_size = 8192

    # Derive original filename
    original_filename = "download"
    try:
        # Provide the same identifying info style as our Danbooru API client
        parsed_for_headers = urlparse(str(payload.url))
        origin = f"{parsed_for_headers.scheme}://{parsed_for_headers.netloc}" if parsed_for_headers.scheme and parsed_for_headers.netloc else ""
        danbooru_style_headers = {
            "User-Agent": "BijutsuBase/0.1.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            # Derive referer/origin from target URL host
            **({"Referer": f"{origin}/"} if origin else {}),
            **({"Origin": origin} if origin else {}),
        }
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=danbooru_style_headers,
        ) as client:
            async with client.stream("GET", str(payload.url)) as resp:
                if resp.status_code >= 400 and resp.status_code < 500:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch URL: {resp.status_code}",
                    )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to fetch URL: {resp.status_code}",
                    )

                # Try filename from Content-Disposition
                cd = resp.headers.get("content-disposition") or resp.headers.get("Content-Disposition")
                if cd and "filename=" in cd:
                    # Very simple parse; quoted or unquoted
                    fname = cd.split("filename=", 1)[1].strip().strip('";')
                    if fname:
                        original_filename = fname
                else:
                    # Fallback to URL path basename
                    parsed = urlparse(str(payload.url))
                    path_name = Path(parsed.path).name
                    if path_name:
                        original_filename = path_name

                # Stream body to temp file with hashing and mime validation
                temp_path, sha256_hash, md5_hash, file_size, mime_type = await _stream_to_temp_and_hash(
                    resp.aiter_bytes(chunk_size=chunk_size)
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error downloading URL")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download URL: {str(e)}",
        )

    # Finalize ingest
    return await _persist_ingest(
        temp_path=temp_path,
        sha256_hash=sha256_hash,
        md5_hash=md5_hash,
        file_size=file_size,
        original_filename=original_filename,
        mime_type=mime_type,
        db=db,
    )


@router.put("/file", response_model=FileResponse, status_code=status.HTTP_200_OK)
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
    
    # Read and stream to temp using shared helper
    chunk_size = 8192

    async def file_chunk_iter() -> AsyncIterator[bytes]:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            yield chunk

    try:
        temp_path, sha256_hash, md5_hash, file_size, file_type = await _stream_to_temp_and_hash(file_chunk_iter())
    finally:
        try:
            await file.close()
        except Exception:
            pass
    
    # Finalize ingest and return response
    return await _persist_ingest(
        temp_path=temp_path,
        sha256_hash=sha256_hash,
        md5_hash=md5_hash,
        file_size=file_size,
        original_filename=original_filename,
        mime_type=file_type,
        db=db,
    )


