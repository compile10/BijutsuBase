"""File storage utilities for BijutsuBase."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.file import File


def generate_file_path(sha256_hash: str, ext: str, thumb: bool = False) -> Path:
    """
    Generate file path based on hash and extension.
    
    Path format: media/<original|thumb>/<first 2 chars>/<next 2 chars>/<hash>.<ext>
    
    Args:
        sha256_hash: SHA256 hash of the file (64 character hex string)
        ext: File extension (without leading dot)
        thumb: If True, generates path for thumbnail; if False, generates path for original (default: False)
    
    Returns:
        Path object representing the file path
    """
    if not sha256_hash or len(sha256_hash) != 64:
        raise ValueError("invalid sha256_hash. must be a 64 character hex string")
    if not ext:
        raise ValueError("ext must be set")
    
    first_two = sha256_hash[:2]
    next_two = sha256_hash[2:4]
    
    # Ensure extension doesn't have leading dot
    ext = ext.lstrip(".")
    
    # Determine subdirectory based on thumb parameter
    subdir = "thumb" if thumb else "original"
    
    filename = f"{sha256_hash}.{ext}"
    return Path("media") / subdir / first_two / next_two / filename


def save_file_to_disk(file: File, content: bytes) -> None:
    """
    Save file content to disk using the generated path.
    
    Creates parent directories if they don't exist.
    
    Args:
        file: File model instance
        content: File content as bytes
    
    Raises:
        ValueError: If file_ext is not set
        OSError: If file cannot be written
    """
    if not file.file_ext:
        raise ValueError("file_ext must be set before saving file to disk")
    
    file_path = generate_file_path(file.sha256_hash, file.file_ext)
    
    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file content
    file_path.write_bytes(content)


def delete_file_from_disk(file: File) -> None:
    """
    Delete file from disk using the generated path.
    
    Silently handles cases where file doesn't exist.
    
    Args:
        file: File model instance
    
    Raises:
        ValueError: If file_ext is not set
        OSError: If file cannot be deleted (other than file not found)
    """
    if not file.file_ext:
        raise ValueError("file_ext must be set before deleting file from disk")
    
    file_path = generate_file_path(file.sha256_hash, file.file_ext)
    
    # Delete file if it exists, ignore if it doesn't
    if file_path.exists():
        file_path.unlink()

